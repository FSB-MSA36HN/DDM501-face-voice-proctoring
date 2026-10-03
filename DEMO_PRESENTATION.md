# Kịch bản bảo vệ DDM501

Lịch trình: **15 phút trình bày + 10–15 phút demo + 10 phút Q&A**. Bản chuẩn dùng demo 13 phút, tổng 38 phút.

## Tài liệu sử dụng

- [PowerPoint](docs/presentation/DDM501_Defense_15p_Demo13p_QA10p.pptx): 18 slide trình bày, 8 slide hướng dẫn demo, 1 slide Q&A và 6 slide phụ lục ẩn khi trình chiếu.
- [PDF slide](docs/presentation/DDM501_Defense_15p_Demo13p_QA10p.pdf).
- [PDF gộp lời thoại, demo và Q&A](docs/presentation/DDM501_Script_Demo_QA.pdf): dùng để tập trước buổi bảo vệ.
- [Lời thoại từng slide](docs/presentation/SPEAKER_SCRIPT.md): người nói, thời lượng, chuyển ý và nguồn đối chiếu.
- [Runbook demo](docs/presentation/DEMO_RUNBOOK.md): chuẩn bị, từng thao tác, kết quả cần kiểm tra, xử lý lỗi và phương án 10/13/15 phút.
- [23 câu hỏi phản biện](docs/presentation/QA_GUIDE.md): câu trả lời, người phụ trách và bằng chứng tham chiếu.

## Nội dung

Phần trình bày bắt đầu bằng tình huống giả định về thi hộ trong đánh giá ngoại ngữ doanh nghiệp, các pain point của HR và phạm vi dịch vụ. Tiếp theo là input/output, kiến trúc, lưu trữ, drift, template update, hiệu chỉnh ngưỡng và lifecycle độc lập Face/Voice.

Demo đi qua ghi danh, xác minh đúng/sai danh tính, lịch sử, evidence, webhook và monitoring. Sau đó trình diễn simulation nâng cấp champion, simulation canary lỗi dẫn tới rollback và khôi phục baseline. Phân biệt dữ liệu tenant demo trong ứng dụng chính với dữ liệu synthetic trong môi trường simulation riêng.

Q&A ưu tiên câu hỏi giảng viên. Nhóm chuẩn bị 23 câu để luyện, dự kiến trả lời khoảng 5–6 câu trong 10 phút. Sáu slide phụ lục dùng khi cần giải thích công thức, ngưỡng, giới hạn và bằng chứng lịch sử.

## Tạo lại tài liệu

Nguồn nội dung: `docs/presentation/deck-content.json`, `DEMO_RUNBOOK.md`, `QA_GUIDE.md`.

```powershell
.venv/Scripts/python.exe pipeline/build_presentation_script.py
powershell -NoProfile -ExecutionPolicy Bypass -File pipeline/build_classroom_presentation.ps1
.venv/Scripts/python.exe pipeline/build_rehearsal_pdf.py
```

Builder slide yêu cầu PowerPoint trên Windows và từ chối ghi đè PPTX đang có. Hãy chuyển bản cũ vào thư mục dự thảo hoặc truyền `-Output` với tên mới. Builder PDF dùng ReportLab và font Segoe UI trên Windows.

Số liệu trong slide evidence là kết quả lịch sử được ghi ngày và nguồn. Trước buổi bảo vệ cần diễn tập trên runtime thực tế, kiểm tra media hợp lệ và độ trễ Airflow. Không diễn giải kết quả simulation thành độ chính xác trên người dùng thật hoặc kết quả fine-tune encoder.
