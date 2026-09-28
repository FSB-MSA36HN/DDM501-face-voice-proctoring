"""Identity-disjoint evaluation matching serving's maximum-template comparison."""
import itertools

import numpy as np


def policy_scores(rows):
    subjects = {}
    for row in rows:
        vector = np.asarray(row['embedding'], dtype=float)
        subjects.setdefault(str(row['person_id']), []).append(vector / np.linalg.norm(vector))
    genuine, impostor = [], []
    for vectors in subjects.values():
        for index, probe in enumerate(vectors):
            references = vectors[:index] + vectors[index + 1:]
            if references:
                genuine.append(max(float(probe @ ref) for ref in references))
    people = sorted(subjects)
    for first, second in itertools.combinations(people, 2):
        impostor.append(max(float(subjects[first][0] @ ref) for ref in subjects[second]))
    return np.asarray(genuine), np.asarray(impostor)


def threshold_trials(positive, negative):
    if min(len(positive), len(negative)) < 5:
        raise ValueError('At least five genuine and impostor comparisons required')
    grid = np.linspace(-0.2, 0.95, 1151)
    return [{'threshold': float(t), 'far': float(np.mean(negative >= t)),
             'frr': float(np.mean(positive < t))} for t in grid]


def select_trial(trials, objective='minimax'):
    if objective == 'minimax':
        return min(trials, key=lambda t: (max(t['far'], t['frr']), t['far'] + t['frr']))
    if objective == 'balanced_error':
        return min(trials, key=lambda t: (t['far'] + t['frr'], max(t['far'], t['frr'])))
    if objective == 'far_constrained':
        return min(trials, key=lambda t: (t['far'] > .05, t['frr'] if t['far'] <= .05 else t['far'], t['far']))
    raise ValueError('Unknown objective')


def identity_evaluation(rows, folds=5):
    people = sorted({str(row['person_id']) for row in rows})
    if len(people) < 10:
        raise ValueError('Identity-disjoint evaluation requires at least ten identities')
    partitions = np.array_split(np.random.default_rng(501).permutation(people), folds)
    results = []
    for index, held_out in enumerate(partitions):
        held_out = set(held_out)
        train = [r for r in rows if str(r['person_id']) not in held_out]
        test = [r for r in rows if str(r['person_id']) in held_out]
        positive, negative = policy_scores(train)
        trials = threshold_trials(positive, negative)
        best = select_trial(trials)
        test_positive, test_negative = policy_scores(test)
        if min(len(test_positive), len(test_negative)) < 5:
            raise ValueError('Insufficient held-out identity comparisons')
        results.append({'fold': index, 'train_identities': sorted({str(r['person_id']) for r in train}),
                        'test_identities': sorted(held_out), 'threshold': best['threshold'],
                        'far': float(np.mean(test_negative >= best['threshold'])),
                        'frr': float(np.mean(test_positive < best['threshold'])),
                        'positive_pairs': len(test_positive), 'negative_pairs': len(test_negative)})
    # Keep fold zero untouched as a documented holdout for the registered threshold.
    held_out = set(partitions[0])
    train_rows = [r for r in rows if str(r['person_id']) not in held_out]
    positive, negative = policy_scores(train_rows)
    trials = threshold_trials(positive, negative)
    best = select_trial(trials)
    metrics = {**{k:best[k] for k in ['far', 'frr']},
               'positive_pairs': len(positive), 'negative_pairs': len(negative),
               'cv_far': float(np.mean([r['far'] for r in results])),
               'cv_frr': float(np.mean([r['frr'] for r in results])),
               'holdout_far': results[0]['far'], 'holdout_frr': results[0]['frr'],
               'holdout_positive_pairs': results[0]['positive_pairs'],
               'holdout_negative_pairs': results[0]['negative_pairs'], 'cv_folds': folds}
    return best['threshold'], metrics, {'method': 'identity-disjoint-max-template',
                                      'registration_holdout_fold': 0, 'folds': results, 'trials': trials}
