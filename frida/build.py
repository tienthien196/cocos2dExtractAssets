#!/usr/bin/env python
# build.py - Script build toàn bộ dự án trong môi trường ảo

import os
import sys
import subprocess
import shutil

def run_command(cmd, shell=False, env=None):
    """Chạy lệnh và kiểm tra kết quả"""
    print(f"\n🔧 Chạy lệnh: {' '.join(cmd) if isinstance(cmd, list) and not shell else cmd}")
    result = subprocess.run(cmd, shell=shell, env=env)
    if result.returncode != 0:
        print(f"❌ Lỗi khi chạy lệnh: {cmd}")
        sys.exit(result.returncode)
    return result

def main():
    print("🚀 Bắt đầu build dự án cocos2dExtractAssets...")

    # === Bước 1: Kiểm tra Python trong venv ===
    if not hasattr(sys, 'real_prefix') and 'VIRTUAL_ENV' not in os.environ:
        print("❌ Cảnh báo: Bạn không đang dùng môi trường ảo (virtual environment)")
        print("Vui lòng kích hoạt venv trước: venv\\Scripts\\activate (Windows) hoặc source venv/bin/activate")
        sys.exit(1)
    else:
        print(f"✅ Đang dùng Python trong venv: {sys.prefix}")

    # === Bước 2: Cài các gói Python cần thiết ===
    print("\n📦 Cài các thư viện Python cần thiết...")
    run_command([
        sys.executable, "-m", "pip", "install",
        "packaging", "jinja2", "argparse", "lief==0.14.0"
    ])

    # === Bước 3: Cài Node.js dependencies (nếu chưa) ===
    if not os.path.exists("node_modules"):
        print("\n📦 Cài Node.js dependencies (frida-compile, ts-frida)...")
        run_command("npm install", shell=True)
    else:
        print("✅ node_modules đã tồn tại, bỏ qua npm install")

    # === Bước 4: Build thư mục C (tạo .so) ===
    so_path = "c/libs/arm64-v8a/libcocos2dExtractAssets.so"
    if not os.path.exists(so_path):
        print(f"\n🛠️  Build thư viện C (tạo {so_path})...")
        run_command(["make", "-C", "c"])
    else:
        print(f"✅ File {so_path} đã tồn tại, bỏ qua bước build C")

    # Kiểm tra lại có file .so không
    if not os.path.exists(so_path):
        print(f"❌ Lỗi: Không tìm thấy file {so_path} sau khi build!")
        print("Hãy kiểm tra Makefile trong thư mục c/ hoặc cài đặt NDK")
        sys.exit(1)

    # === Bước 5: Chạy so2ts.py để sinh file .ts ===
    ts_output_dir = "agent/modinfos"
    ts_output_file = os.path.join(ts_output_dir, "libcocos2dExtractAssets_arm64.ts")
    os.makedirs(ts_output_dir, exist_ok=True)

    print(f"\n🧠 Phân tích .so và sinh TypeScript: {ts_output_file}")
    so2ts_script = "node_modules/ts-frida/dist/bin/so2ts.py"
    if not os.path.exists(so2ts_script):
        print(f"❌ Không tìm thấy {so2ts_script}. Hãy chắc chắn đã chạy 'npm install'")
        sys.exit(1)

    run_command([
        sys.executable, so2ts_script,
        "--no-content",
        "-b", so_path,
        "-o", ts_output_file
    ])

    # === Bước 6: Biên dịch agent TypeScript thành _agent.js ===
    print("\n📜 Biên dịch TypeScript thành _agent.js...")
    if not os.path.exists("agent/index.ts"):
        print("❌ Không tìm thấy agent/index.ts")
        sys.exit(1)

    run_command(["npx", "frida-compile", "agent/index.ts", "-o", "_agent.js"], shell=True)

    # === Hoàn thành ===
    print("\n🎉 Build thành công!")
    print("📄 File agent đã được tạo: _agent.js")
    print("📤 Bạn có thể dùng file này với Frida để inject vào ứng dụng.")

if __name__ == "__main__":
    main()