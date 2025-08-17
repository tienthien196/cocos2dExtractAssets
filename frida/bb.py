#!/usr/bin/env python3
# build_and_push.py
# Script thay thế Makefile: build và push .so lên thiết bị Android

import os
import subprocess
import sys

# ================== CẤU HÌNH ==================
# ✅ Đặt NDK_PATH: trỏ đến thư mục GỐC của NDK, KHÔNG phải ...\build
NDK_PATH = r"C:\android-ndk-r15c"  # <-- SỬA ĐƯỜNG DẪN NẾU CẦN

# Nếu bạn muốn dùng biến môi trường: bỏ comment dòng dưới
# NDK_PATH = os.getenv("NDK_PATH", r"C:\android-ndk-r15c")


ADB = "adb"                     # Đảm bảo adb ở trong PATH
PROJECT_ROOT = "./c"              # <-- Sửa ở đây
LIBS_DIR = "../frida/c/libs"  
# ================== HÀM HỖ TRỢ ==================

def run_command(cmd, shell=True, check=True, cwd=None):
    """Chạy lệnh và in ra màn hình"""
    print(f"[RUN] {cmd}")
    try:
        result = subprocess.run(cmd, shell=shell, cwd=cwd, check=check)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Lệnh thất bại với mã {e.returncode}")
        print(f"   {cmd}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Lỗi hệ thống khi chạy lệnh: {e}")
        sys.exit(1)

def check_ndk_path():
    """Kiểm tra NDK_PATH hợp lệ và tồn tại ndk-build.cmd"""
    global NDK_PATH

    if not NDK_PATH:
        print("❌ Lỗi: NDK_PATH chưa được định nghĩa.")
        print("Vui lòng đặt NDK_PATH trong script hoặc môi trường.")
        sys.exit(1)

    if not os.path.isdir(NDK_PATH):
        print(f"❌ Thư mục NDK không tồn tại: {NDK_PATH}")
        sys.exit(1)

    ndk_build = os.path.join(NDK_PATH, "ndk-build.cmd")
    if not os.path.isfile(ndk_build):
        print(f"❌ Không tìm thấy ndk-build.cmd tại: {ndk_build}")
        print("💡 Kiểm tra: NDK_PATH phải trỏ đến thư mục GỐC của NDK (ví dụ: C:\\android-ndk-r15c)")
        sys.exit(1)

    print(f"✅ NDK_PATH hợp lệ: {NDK_PATH}")
    return ndk_build

def build():
    """Build dự án bằng ndk-build"""
    print("🔨 Bắt đầu build native code...")
    ndk_build_cmd = os.path.join(NDK_PATH, "ndk-build.cmd")
    cmd = f'"{ndk_build_cmd}" V=1 -C "{PROJECT_ROOT}"'
    run_command(cmd)
    print("✅ Build thành công!")

def clean():
    """Dọn dẹp file build"""
    print("🧹 Dọn dẹp file build...")
    ndk_build_cmd = os.path.join(NDK_PATH, "ndk-build.cmd")
    cmd = f'"{ndk_build_cmd}" clean -C "{PROJECT_ROOT}"'
    run_command(cmd)
    print("✅ Đã dọn dẹp.")

def get_device_abi():
    """Lấy ABI chính của thiết bị đang kết nối"""
    try:
        result = subprocess.run(
            [ADB, "shell", "getprop", "ro.product.cpu.abilist"],
            capture_output=True,
            text=True,
            check=True
        )
        abilist = result.stdout.strip().split(',')
        abilist = [abi.strip() for abi in abilist if abi.strip()]

        if not abilist:
            print("❌ Không thể lấy ABI từ thiết bị.")
            return None

        print(f"📱 Thiết bị hỗ trợ các ABI: {', '.join(abilist)}")

        if "arm64-v8a" in abilist:
            return "arm64-v8a"
        elif "armeabi-v7a" in abilist:
            return "armeabi-v7a"
        else:
            print(f"❌ Không hỗ trợ các ABI: {abilist}")
            return None
    except Exception as e:
        print(f"❌ Lỗi khi kết nối thiết bị: {e}")
        return None

def push_libs(abi):
    """Push tất cả file .so trong thư mục libs/abi lên thiết bị"""
    libs_path = os.path.join(LIBS_DIR, abi)
    if not os.path.isdir(libs_path):
        print(f"❌ Thư mục không tồn tại: {libs_path}")
        print("💡 Chạy 'python build_and_push.py' để build trước.")
        sys.exit(1)

    so_files = [f for f in os.listdir(libs_path) if f.endswith(".so")]
    if not so_files:
        print(f"❌ Không tìm thấy file .so trong {libs_path}")
        sys.exit(1)

    print(f"📤 Đang push {len(so_files)} file .so đến /data/local/tmp")
    for so_file in so_files:
        src = os.path.join(libs_path, so_file)
        cmd = f'{ADB} push "{src}" /data/local/tmp/'
        run_command(cmd)

    print("✅ Đã push thành công lên thiết bị!")

# ================== CHÍNH ==================
def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "clean":
            clean()
            return
        else:
            print(f"❌ Lệnh không hợp lệ: {sys.argv[1]}")
            print("Sử dụng:")
            print("  python build_and_push.py          - Build và push")
            print("  python build_and_push.py clean    - Dọn dẹp")
            sys.exit(1)

    # Kiểm tra ADB
    try:
        subprocess.run([ADB, "devices"], check=True, capture_output=True)
    except:
        print("❌ ADB không hoạt động. Vui lòng:")
        print("  1. Kết nối thiết bị Android")
        print("  2. Bật USB Debugging")
        print("  3. Đảm bảo 'adb' có trong PATH")
        sys.exit(1)

    # Các bước chính
    check_ndk_path()
    build()

    abi = get_device_abi()
    if not abi:
        sys.exit(1)

    push_libs(abi)

if __name__ == "__main__":
    main()