import os
import json
import uuid

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:18100").rstrip("/")
st.set_page_config(page_title="Face + Voice SaaS Portal", page_icon="🛡️", layout="wide")
API_KEY = st.sidebar.text_input("API key của tổ chức / quản trị", type="password")
HEADERS = {"X-API-Key": API_KEY}

st.title("🛡️ Face + Voice SaaS Portal")
st.caption("Quản lý xác minh danh tính, tích hợp hệ thống thi và vận hành MLOps")
if not API_KEY:
    st.info("Nhập API key được cấp để đăng nhập. Mỗi tổ chức chỉ truy cập dữ liệu của mình.")
    st.stop()


def api(method: str, path: str, **kwargs):
    response = requests.request(method, f"{API_URL}{path}", headers=HEADERS, timeout=120, **kwargs)
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"HTTP {response.status_code}: {detail}")
    return response.json()


try:
    identity = api("GET", "/v1/me")
    st.sidebar.caption(f"Tenant: {identity['tenant_id']} · {identity['role']}")
    health = api("GET", "/health")
    st.sidebar.success(f"API healthy · {health['backend']} · model {health['model_version']}")
except Exception as exc:
    st.sidebar.error(f"API chưa sẵn sàng: {exc}")
    st.stop()

pages = ["Tổng quan", "Thêm hồ sơ", "Phiên xác minh"]
if identity["role"] in {"operator", "platform"}:
    pages += ["Ghi danh sinh trắc", "Xác minh", "Sự kiện", "Webhook & Audit"]
if identity["role"] == "platform":
    pages += ["Khách hàng & API keys", "Vận hành full pipeline"]
page = st.sidebar.radio("Chức năng", pages)

if page == "Tổng quan":
    st.subheader("Luồng demo")
    st.markdown("1. Tạo hồ sơ → 2. Ghi danh ít nhất 2 ảnh và 2 audio WAV → 3. Xác minh → 4. Kiểm tra event/Grafana.")
    try:
        people = api("GET", "/v1/people")
        c1, c2, c3 = st.columns(3)
        c1.metric("Hồ sơ", len(people))
        c2.metric("Sẵn sàng", sum(person["ready"] for person in people))
        c3.metric("Cần bổ sung mẫu", sum(not person["ready"] for person in people))
        if people:
            st.dataframe(pd.DataFrame(people), use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(str(exc))

elif page == "Thêm hồ sơ":
    with st.form("create-person", clear_on_submit=True):
        external_id = st.text_input("Mã nhân viên / thí sinh", placeholder="EMP-0001")
        display_name = st.text_input("Tên hiển thị", placeholder="Nguyễn Văn A")
        submitted = st.form_submit_button("Tạo hồ sơ", type="primary")
    if submitted:
        try:
            created = api("POST", "/v1/people", json={"external_id": external_id, "display_name": display_name})
            st.success(f"Đã tạo {created['display_name']} · ID {created['id']}")
        except Exception as exc:
            st.error(str(exc))

elif page == "Ghi danh sinh trắc":
    try:
        people = api("GET", "/v1/people")
    except Exception as exc:
        people = []
        st.error(str(exc))
    if not people:
        st.info("Hãy tạo hồ sơ trước.")
    else:
        labels = {f"{p['external_id']} — {p['display_name']} ({p['face_samples']}F/{p['voice_samples']}V)": p for p in people}
        selected = labels[st.selectbox("Hồ sơ", labels)]
        st.info("Cần ≥2 ảnh ở góc/ánh sáng hơi khác nhau và ≥2 đoạn WAV, mỗi đoạn 2–10 giây.")
        camera = st.camera_input("Chụp ảnh trực tiếp")
        face_uploads = st.file_uploader("Hoặc tải nhiều ảnh", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
        voice_recording = st.audio_input("Thu giọng nói: đọc một câu tiếng Anh")
        voice_uploads = st.file_uploader("Hoặc tải nhiều audio WAV", type=["wav"], accept_multiple_files=True)
        if st.button("Ghi danh các mẫu", type="primary"):
            files = []
            for item in ([camera] if camera else []) + face_uploads:
                files.append(("face_files", (item.name, item.getvalue(), item.type or "image/jpeg")))
            for item in ([voice_recording] if voice_recording else []) + voice_uploads:
                files.append(("voice_files", (item.name, item.getvalue(), "audio/wav")))
            try:
                result = api("POST", f"/v1/people/{selected['id']}/enroll", files=files)
                st.success(f"Đã thêm {result['face_added']} ảnh, {result['voice_added']} audio. Ready={result['ready']}")
                if result["rejected"]:
                    st.warning("\n".join(result["rejected"]))
            except Exception as exc:
                st.error(str(exc))

elif page == "Xác minh":
    try:
        people = [person for person in api("GET", "/v1/people") if person["ready"]]
    except Exception as exc:
        people = []
        st.error(str(exc))
    if not people:
        st.info("Chưa có hồ sơ đủ mẫu.")
    else:
        labels = {f"{p['external_id']} — {p['display_name']}": p for p in people}
        selected = labels[st.selectbox("Danh tính khai báo", labels)]
        session_id = st.text_input("Session ID", value=f"exam-{uuid.uuid4().hex[:8]}")
        face = st.camera_input("Ảnh xác minh")
        voice = st.audio_input("Audio xác minh")
        if st.button("Xác minh", type="primary"):
            files = {}
            if face:
                files["face_file"] = (face.name, face.getvalue(), face.type or "image/jpeg")
            if voice:
                files["voice_file"] = (voice.name, voice.getvalue(), "audio/wav")
            try:
                result = api("POST", "/v1/verify", data={"person_id": selected["id"], "session_id": session_id}, files=files)
                if result["accepted"]:
                    st.success("ALLOW — hai tín hiệu khớp ngưỡng")
                else:
                    st.warning("REVIEW — chuyển kiểm tra thủ công")
                st.json(result)
            except Exception as exc:
                st.error(str(exc))

elif page == "Sự kiện":
    try:
        events = api("GET", "/v1/events?limit=200")
        if events:
            frame = pd.DataFrame(events)
            st.dataframe(frame, use_container_width=True, hide_index=True)
            st.download_button("Tải CSV", frame.to_csv(index=False), "verification-events.csv", "text/csv")
            st.subheader("Phản hồi kiểm duyệt")
            event_id = st.selectbox("Event", [event["id"] for event in events])
            is_genuine = st.radio("Nhãn thực tế", [True, False], format_func=lambda value: "Genuine" if value else "Impostor")
            reviewer = st.text_input("Reviewer", value="proctor-demo")
            notes = st.text_area("Ghi chú")
            if st.button("Lưu ground truth"):
                try:
                    api("PUT", f"/v1/events/{event_id}/feedback", json={"is_genuine": is_genuine, "reviewer": reviewer, "notes": notes or None})
                    st.success("Đã lưu feedback cho performance monitoring")
                except Exception as exc:
                    st.error(str(exc))
        else:
            st.info("Chưa có sự kiện.")
    except Exception as exc:
        st.error(str(exc))

elif page == "Phiên xác minh":
    try:
        people = [p for p in api("GET", "/v1/people") if p["ready"]]
        if people:
            labels = {f"{p['external_id']} — {p['display_name']}": p for p in people}
            selected = labels[st.selectbox("Thí sinh đã ghi danh", labels)]
            exam = st.text_input("Mã ca thi", value="ENGLISH-DEMO-501")
            if st.button("Tạo phiên mới"):
                result = api("POST", "/v1/sessions", json={"person_id": selected["id"], "exam_id": exam,
                                                          "request_id": str(uuid.uuid4())})
                st.link_button("Mở trang verify có thời hạn", result["verify_url"])
                st.warning("Link chỉ dành cho thí sinh này; không chia sẻ công khai.")
        rows = api("GET", "/v1/sessions")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        pending = [row for row in rows if row["status"] == "review"]
        if pending and identity["role"] in {"operator", "platform"}:
            st.subheader("Quyết định thủ công")
            session_id = st.selectbox("Phiên chờ review", [row["id"] for row in pending])
            approved = st.checkbox("Cho phép vào thi sau kiểm tra")
            notes = st.text_area("Lý do quyết định (tối thiểu 5 ký tự)")
            if st.button("Lưu quyết định và gửi webhook"):
                api("POST", f"/v1/sessions/{session_id}/review", json={"approved": approved, "notes": notes})
                st.success("Đã lưu; quyết định model ban đầu vẫn được giữ để audit.")
    except Exception as exc:
        st.error(str(exc))

elif page == "Webhook & Audit":
    try:
        rows = api("GET", "/v1/webhooks")
        st.subheader("Webhook deliveries")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        failed = [row["id"] for row in rows if row["status"] == "failed"]
        if failed:
            delivery = st.selectbox("Delivery lỗi", failed)
            if st.button("Thử gửi lại"):
                api("POST", f"/v1/webhooks/{delivery}/retry")
                st.success("Đã đưa lại vào hàng đợi")
        st.subheader("Audit log")
        st.dataframe(pd.DataFrame(api("GET", "/v1/audit")), use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(str(exc))

elif page == "Khách hàng & API keys":
    try:
        tenants = api("GET", "/v1/admin/tenants")
        st.dataframe(pd.DataFrame(tenants), use_container_width=True, hide_index=True)
        with st.form("tenant"):
            name = st.text_input("Tên tổ chức")
            webhook = st.text_input("Webhook URL (host phải có trong allowlist)")
            return_url = st.text_input("URL quay về hệ thống khách hàng")
            if st.form_submit_button("Tạo khách hàng"):
                result = api("POST", "/v1/admin/tenants", json={"name": name, "webhook_url": webhook or None,
                                                              "return_url": return_url or None})
                st.warning("Lưu webhook secret vào secret manager của khách hàng.")
                st.json(result)
        selected = st.selectbox("Khách hàng cấp key", tenants, format_func=lambda t: t["name"])
        role = st.selectbox("Quyền", ["operator", "integration"])
        if st.button("Cấp API key mới"):
            result = api("POST", f"/v1/admin/tenants/{selected['id']}/keys", json={"role": role})
            st.warning("API key chỉ hiển thị ở lần cấp này. Không đưa integration key vào JavaScript trình duyệt.")
            st.code(result["api_key"])
        keys = api("GET", f"/v1/admin/tenants/{selected['id']}/keys")
        st.dataframe(pd.DataFrame(keys), use_container_width=True, hide_index=True)
        active = [key["id"] for key in keys if key["active"]]
        if active:
            key_id = st.selectbox("Key thu hồi", active)
            if st.button("Thu hồi key"):
                api("DELETE", f"/v1/admin/keys/{key_id}")
                st.success("Đã thu hồi")
    except Exception as exc:
        st.error(str(exc))

elif page == "Vận hành full pipeline":
    st.subheader("Monitoring tập trung")
    st.link_button("Mở Grafana Monitoring Centre", os.getenv("PUBLIC_GRAFANA_URL", "http://localhost:13000/d/biometric-overview"), type="primary")
    st.caption("Xem service health, dữ liệu, drift, performance, Registry, review queue, Airflow, RAI, tài nguyên, logs và các báo cáo tại Grafana. Cảnh báo gửi tới Telegram.")
    st.subheader("Quản trị pipeline")
    links = {
        "Ứng dụng thi cũ giả lập": "http://localhost:18600", "API / Swagger": "http://localhost:18100/docs",
        "API health": "http://localhost:18100/health", "Airflow": "http://localhost:18081",
        "MLflow Registry": "http://localhost:15030", "MinIO Console": "http://localhost:19101",
        "GitHub Actions": "https://github.com/TrinhDucDuong/ddm501-face-voice-proctoring/actions",
    }
    links.update(json.loads(os.getenv("PORTAL_LINKS_JSON") or "{}"))
    for label, url in links.items():
        st.link_button(label, url)
    if st.button("Reload champion từ MLflow"):
        try:
            st.json(api("POST", "/v1/admin/reload-model"))
        except Exception as exc:
            st.error(str(exc))
