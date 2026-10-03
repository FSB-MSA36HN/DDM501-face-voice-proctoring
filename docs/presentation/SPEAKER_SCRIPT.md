# Kịch bản Thuyết trình: Face + Voice Integrity

_Cập nhật: 03/10/2026. Đồng bộ với slide `DDM501_Defense_15p_Demo13p_QA10p.pdf` (Slide 1 đến 18)._

**Khung thời gian:** Thuyết trình 10 phút, Q&A 10 phút. Phần Demo đã được lược bỏ theo cấu trúc mới.
**Mục tiêu:** Trình bày mượt mà, súc tích, chuyên nghiệp. Không sa đà vào đọc slide mà giải thích logic đằng sau. Mỗi người trình bày khoảng 2.5 phút.

## Phân vai (18 Slide chính)

| Người nói           | Slide   | Nội dung chính                                                               |
| ------------------- | ------- | ---------------------------------------------------------------------------- |
| **Trịnh Đức Dương** | 1 – 5   | Đặt vấn đề, khó khăn, giải pháp và mô hình tích hợp.                         |
| **Tô Thanh Hải**    | 6 – 9   | Logic kiểm tra, cơ chế AI (Model), kiến trúc hệ thống và lưu trữ.            |
| **Đỗ Quang Hiệp**   | 10 – 13 | Vấn đề trôi dữ liệu (Drift), các lớp đánh giá, và luồng ra quyết định.       |
| **Ngô Anh Đức**     | 14 – 18 | Luồng kiểm định Model (Gate/Canary), CI/CD, chuẩn bị triển khai và Tổng kết. |

---

## Phần 1: Đặt vấn đề & Giải pháp

**Người nói: Trịnh Đức Dương (00:00 – 02:30)**

### Slide 01: Tiêu đề

Kính chào hội đồng và các bạn. Hôm nay, nhóm chúng em xin trình bày dự án **Face & Voice Integrity** – Giải pháp xác minh danh tính và chống gian lận dành cho các kỳ thi ngoại ngữ trực tuyến của doanh nghiệp.

### Slide 02: Đặt vấn đề

Hãy hình dung một bối cảnh rất phổ biến: 8h55, một nhân viên đăng nhập tài khoản hợp lệ để thi. Tuy nhiên, đến 9h10 ở phần thi nói, một người khác có năng lực tốt hơn lại ngồi vào hỗ trợ hoặc thi thay.
Hệ thống thi thông thường vẫn ghi nhận bài làm cho tài khoản ban đầu. Kết quả sai lệch này dẫn đến những quyết định nhân sự sai lầm phía sau, và bộ phận HR thì hoàn toàn thiếu bằng chứng để xác minh lại. Đó là bài toán chúng em muốn giải quyết.

### Slide 03: Khó khăn

Việc phát hiện gian lận thủ công gặp 3 khó khăn lớn:

1. **Độ tin cậy:** Không dám chắc người làm bài có đúng là chủ tài khoản không.
2. **Khối lượng rà soát:** Dù có camera ghi hình, HR cũng không thể xem lại hàng ngàn giờ video để tìm khoảnh khắc gian lận.
3. **Nguy cơ kết luận nhầm:** Một người làm bài trung thực vẫn có thể bị điểm hệ thống đánh giá thấp chỉ vì đổi thiết bị, thiếu sáng, hoặc ảnh gốc đã quá cũ.
   Vì vậy, hệ thống không chỉ cần "phát hiện", mà phải đưa ra "lý do" và "bằng chứng" chuẩn xác.

### Slide 04: Hệ thống kiểm tra những dấu hiệu nào?

Giải pháp của nhóm tập trung vào 4 tín hiệu chính:

- So khớp khuôn mặt và giọng nói với mẫu gốc.
- Phát hiện ảnh giả hoặc âm thanh phát lại (Face PAD & Audio Anti-spoof).
- Phát hiện có nhiều người trong khung hình hoặc bị đổi giọng.
- Chống dùng lại (replay) cùng một đoạn video/audio trong phiên thi.
  Chúng em không tham vọng bắt được _mọi_ thủ thuật gian lận (như nhắc bài ngoài camera), nên hệ thống đóng vai trò cung cấp _tín hiệu nghi vấn (suspicious)_ để HR ra quyết định, chứ không tự động hủy bài thi.

### Slide 05: Bổ sung xác minh vào phần mềm thi

Về mô hình kinh doanh, chúng em cung cấp giải pháp dưới dạng **Dịch vụ tích hợp (API)**.
Doanh nghiệp vẫn hoàn toàn làm chủ hệ thống thi, điểm số và bài làm. Dịch vụ của nhóm chỉ nhận dữ liệu, xử lý xác minh và trả về kết quả kèm bằng chứng qua API/Webhook để doanh nghiệp lưu trữ. Tiếp theo, bạn Hải sẽ làm rõ luồng hoạt động này.

---

## Phần 2: Kiến trúc & Vận hành Core

**Người nói: Tô Thanh Hải (02:30 – 05:00)**

### Slide 06: Logic kiểm tra

Luồng xử lý diễn ra qua 5 bước rất tinh gọn:
Từ lúc nhân viên cung cấp mẫu ghi danh chuẩn (Ghi danh), đến lúc hệ thống thi gửi dữ liệu (Gửi capture). API của chúng em sẽ nhận dữ liệu, thực hiện đối chiếu chéo (Xác minh) và trả ngay kết quả, đồng thời gửi thông báo bất đồng bộ qua Webhook. HR sau đó chỉ cần lên Portal để xem lại lịch sử và bằng chứng.

### Slide 07: Model biến ảnh và giọng nói thành quyết định

Vậy hệ thống xác minh thế nào?
Với hình ảnh, chúng em dùng YuNet để dò tìm khuôn mặt và SFace để trích xuất đặc trưng (Embedding). Với âm thanh, model ECAPA được sử dụng.
Các đặc trưng này sẽ được so sánh (Cosine similarity) với mẫu gốc của chính nhân viên đó.
Điều đặc biệt là nhóm **không huấn luyện lại toàn bộ model nhận diện**, mà chỉ huấn luyện lại **Ngưỡng quyết định (Threshold Policy)** để phù hợp với phân phối dữ liệu của từng doanh nghiệp.

### Slide 08: Serving, MLOps, và Monitoring

Đây là bức tranh tổng thể của kiến trúc:

- **Serving:** Nhận request và trả kết quả realtime (FastAPI).
- **MLOps:** Tự động hóa việc đánh giá và cập nhật mô hình với Airflow và MLflow.
- **Vận hành (Monitoring):** Thu thập toàn bộ log và metrics bằng Prometheus và hiển thị trực quan trên Grafana.
  Tất cả chạy trên môi trường Docker Compose, dễ dàng đóng gói và triển khai.

### Slide 09: Lưu đúng bằng chứng

Về lưu trữ, chúng em tách bạch rõ ràng:

- **PostgreSQL** lưu trữ các đoạn mã đặc trưng (Embedding JSON) và lịch sử.
- **MinIO (S3)** được dùng để lưu riêng các file hình ảnh/âm thanh _nghi vấn_ làm bằng chứng.
  Sau khi hệ thống vận hành, dữ liệu sẽ dần biến đổi. Bạn Hiệp sẽ giải thích cơ chế hệ thống tự thích nghi với điều này.

---

## Phần 3: Quản lý độ trôi dữ liệu (Drift) & Tự động hóa

**Người nói: Đỗ Quang Hiệp (05:00 – 07:30)**

### Slide 10: Score giảm có thể đến từ nhiều nguyên nhân

Khi tỷ lệ nhận diện đúng giảm xuống, chưa chắc là do AI kém đi.
Có thể do camera hôm nay tối hơn (Capture thay đổi), hoặc ảnh thẻ đăng ký cách đây 2 năm không còn giống hiện tại (Template đã cũ). Chỉ khi nguyên nhân nằm ở bản thân model không còn tương thích tốt (Policy suy giảm), chúng ta mới cần huấn luyện lại.

### Slide 11: Năm lớp bằng chứng để đánh giá Drift

Để không kết luận vội vàng, hệ thống đánh giá dữ liệu qua 5 lớp:

1. **Quality (Đầu vào):** Dùng chỉ số PSI để xem ánh sáng, tiếng ồn có thay đổi không.
2. **Embedding:** Dùng chỉ số MMD để xem khuôn mặt/giọng nói có lệch chuẩn không.
3. **Score:** So sánh điểm tương đồng.
4. **Performance:** Tính toán tỷ lệ sai sót (FMR, FNMR) từ các mẫu đã được review.
5. **Template Age:** Phân tích xem lỗi tập trung ở người mới hay người cũ.

### Slide 12: Decision Engine

Từ 5 lớp trên, bộ máy ra quyết định (Airflow) sẽ chẩn đoán:

- Nếu chỉ do ánh sáng kém -> Báo **INPUT_DRIFT** (Cần kiểm tra camera).
- Nếu dữ liệu đã cũ -> Báo **TEMPLATE_UPDATE_REQUIRED** (Cần nhắc nhân viên cập nhật ảnh/giọng nói).
- Chỉ khi mọi bằng chứng chỉ ra model đang thực sự kém đi trên diện rộng -> Hệ thống mới chốt trạng thái **RETRAIN_REQUIRED** để tự động hiệu chỉnh model.

### Slide 13: Cập nhật Template và Retrain

Chúng em chia làm hai luồng rõ rệt:

- **Update Template:** Chỉ lấy những mẫu có chất lượng thật tốt, điểm cao và nhất quán để cập nhật lại mẫu gốc cho nhân viên, giúp model nhận diện mượt hơn.
- **Retrain Threshold:** Airflow sẽ khóa snapshot dữ liệu hiện tại, chạy huấn luyện lại ngưỡng quyết định (threshold) và tạo ra một model mới gọi là Candidate. Mời bạn Đức tiếp tục với luồng kiểm định model này.

---

## Phần 4: Luồng Triển khai & Tổng kết

**Người nói: Ngô Anh Đức (07:30 – 10:00)**

### Slide 14: Model mới phải vượt qua Offline và Traffic Gate

Model mới (Candidate) không được phép đưa vào dùng ngay.
Đầu tiên nó phải vượt qua bài test **Offline** trên dữ liệu lịch sử. Nếu tốt hơn bản cũ (Champion), nó thăng cấp thành **Challenger** và vào trạng thái **Shadow** – chạy ngầm cùng bản cũ nhưng không can thiệp kết quả. Cuối cùng là **Canary** – bắt đầu phục vụ một lượng nhỏ traffic thật tăng dần.

### Slide 15: Canary Stage

Tại các bước Canary (5%, 10%, 25%,...), hệ thống khắt khe đánh giá: tỷ lệ nhận nhầm (FMR) bắt buộc phải dưới 1% và không được tăng so với bản cũ. Nếu bất kỳ chỉ số nào vi phạm, traffic lập tức bị ngắt, quay về dùng bản cũ (Rollback). Chỉ khi trót lọt tới 100%, bản mới mới chính thức thay thế.

### Slide 16: CI/CD & Lifecycle

Sự phân bạch nằm ở đây:

- Khi có thay đổi về **Code ứng dụng**, chúng em dùng CI/CD (GitHub Actions) để chạy test và tự động deploy qua Docker.
- Khi có thay đổi về **Logic Model (Policy)**, luồng MLOps nội bộ với Shadow/Canary sẽ tự động tiếp quản mà không cần can thiệp code hay khởi động lại server.

### Slide 17: Kiểm chứng trước khi triển khai

Dự án hiện tại là một bản chứng minh concept (PoC) hoàn chỉnh về MLOps. Để mang vào thực tế, cần 3 yếu tố: Dữ liệu thật có sự đồng thuận (Consented data), đo đạc tải thực tế cho hàng chục ngàn nhân viên, và hiệu chỉnh lại các ngưỡng (Gate) phù hợp với rủi ro của công ty.

### Slide 18: Tổng kết

Tóm lại, dự án **Face & Voice Integrity** không chỉ giải bài toán "Gian lận", mà còn cung cấp một bộ khung hạ tầng AI (MLOps) đáng tin cậy. Dịch vụ đưa ra lý do và bằng chứng minh bạch, đồng thời tự động đánh giá, cảnh báo và thay thế mô hình an toàn khi dữ liệu biến đổi.

Cảm ơn hội đồng và các bạn đã lắng nghe. Chúng em xin phép chuyển sang phần Q&A.

---

## Phụ lục (Chỉ mở khi có câu hỏi Q&A)

_(Người nói: Ai có thế mạnh phần nào sẽ trả lời phần đó. Đức điều hướng slide)_

- **Slide 28 (Công thức):** Giải thích công thức PSI (đo drift) và MMD (đo lệch vector embedding), cùng cách tính FMR/FNMR.
- **Slide 29 (Cấu hình):** Giải thích vì sao demo nhanh hơn thực tế (giảm số lượng mẫu và thời gian chờ để kịp chiếu).
- **Slide 30 (Hiểu nhầm):** Khẳng định lại: Không train lại mạng nơ-ron lõi, không lưu vector database chuyên dụng, Canary là rẽ nhánh logic chứ không phải chạy 2 server.
- **Slide 31-33:** Trách nhiệm nhóm, Coverage test (82.03%) và nguồn đối chiếu minh bạch.
