#!/usr/bin/env python3
# build_and_push.py
# Script đầy đủ: build .so → sinh modinfo → push → biên dịch _agent.js
# ✅ Hỗ trợ nhiều thiết bị, chọn bằng -s hoặc tự động

import os
import subprocess
import sys

# ================== CẤU HÌNH ==================
# ✅ Đặt NDK_PATH: trỏ đến thư mục GỐC của NDK
NDK_PATH = r"C:\android-ndk-r15c"  # <-- SỬA ĐƯỜNG DẪN NẾU CẦN
# Hoặc dùng biến môi trường:
# NDK_PATH = os.getenv("NDK_PATH", r"C:\android-ndk-r15c")

ADB = "adb"
PROJECT_ROOT = "./c"                    # Thư mục chứa Android.mk
LIBS_DIR = "../frida/c/libs"            # Nơi lưu .so sau khi build
AGENT_DIR = "../frida/agent"            # Thư mục chứa agent/index.ts
MODINFO_DIR = os.path.join(AGENT_DIR, "modinfos")
AGENT_OUTPUT = "../frida/_agent.js"     # File kết quả sau frida-compile

# Thiết bị mặc định (nếu không chỉ định)
DEFAULT_DEVICE_ID = "127.0.0.1:5555"  # BlueStacks
# DEFAULT_DEVICE_ID = "emulator-5554"  # AVD

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
    """Kiểm tra NDK_PATH hợp lệ"""
    global NDK_PATH

    if not NDK_PATH:
        print("❌ Lỗi: NDK_PATH chưa được định nghĩa.")
        print("Vui lòng đặt NDK_PATH trong script hoặc môi trường.")
        sys.exit(1)

    if not os.path.isdir(NDK_PATH):
        print(f"❌ Thư mục NDK không tồn tại: {NDK_PATH}")
        sys.exit(1)

    # Xác định ndk-build (Windows: .cmd, Unix: không)
    ndk_build = os.path.join(NDK_PATH, "ndk-build.cmd" if os.name == 'nt' else "ndk-build")
    if not os.path.isfile(ndk_build):
        print(f"❌ Không tìm thấy ndk-build tại: {ndk_build}")
        print("💡 Kiểm tra: NDK_PATH phải trỏ đến thư mục GỐC của NDK")
        sys.exit(1)

    print(f"✅ NDK_PATH hợp lệ: {NDK_PATH}")
    return ndk_build

def build():
    """Build dự án bằng ndk-build"""
    print("🔨 Bắt đầu build native code...")
    ndk_build_cmd = os.path.join(NDK_PATH, "ndk-build.cmd" if os.name == 'nt' else "ndk-build")
    cmd = f'"{ndk_build_cmd}" V=1 -C "{PROJECT_ROOT}"'
    run_command(cmd)
    print("✅ Build thành công!")

def clean():
    """Dọn dẹp file build"""
    print("🧹 Dọn dẹp file build...")
    ndk_build_cmd = os.path.join(NDK_PATH, "ndk-build.cmd" if os.name == 'nt' else "ndk-build")
    cmd = f'"{ndk_build_cmd}" clean -C "{PROJECT_ROOT}"'
    run_command(cmd)
    print("✅ Đã dọn dẹp.")

def get_device_abi(device_id=None):
    """Lấy ABI chính của thiết bị đang kết nối"""
    cmd = [ADB]
    if device_id:
        cmd += ["-s", device_id]
    cmd += ["shell", "getprop", "ro.product.cpu.abilist"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
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

def convert_so_to_ts(abi):
    """Chuyển .so thành file modinfo .ts bằng so2ts.py"""
    so_path = os.path.join(LIBS_DIR, abi, "libcocos2dExtractAssets.so")
    # Chuyển ABI thành tên ngắn gọn
    if abi == "arm64-v8a":
        short_name = "arm64"
    elif abi == "armeabi-v7a":
        short_name = "arm"
    else:
        short_name = abi.replace('-', '_')

    ts_output = os.path.join(MODINFO_DIR, f"libcocos2dExtractAssets_{short_name}.js")

    if not os.path.isfile(so_path):
        print(f"❌ Không tìm thấy .so để chuyển: {so_path}")
        sys.exit(1)

    # Đường dẫn đến so2ts.py
    so2ts_path = os.path.join("node_modules", "ts-frida", "dist", "bin", "so2ts.py")
    if not os.path.isfile(so2ts_path):
        print(f"❌ Không tìm thấy so2ts.py tại: {so2ts_path}")
        print("💡 Chạy: npm install ts-frida")
        sys.exit(1)

    # Tạo thư mục modinfos nếu chưa có
    os.makedirs(MODINFO_DIR, exist_ok=True)

    cmd = [
        "python", so2ts_path,
        "--no-content",
        "-b", so_path,
        "-o", ts_output
    ]

    print(f"🔄 Đang sinh modinfo: {so_path} → {ts_output}")
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Sinh modinfo thành công: {ts_output}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Lỗi khi chạy so2ts.py: {e}")
        sys.exit(1)

def compile_agent():
    """Biên dịch agent/index.ts → _agent.js bằng frida-compile"""
    print("🔄 Biên dịch agent/index.ts → _agent.js...")
    agent_ts_path = os.path.join(AGENT_DIR, "index.ts")
    if not os.path.isfile(agent_ts_path):
        print(f"❌ Không tìm thấy agent/index.ts tại: {agent_ts_path}")
        sys.exit(1)

    cmd = f"npx frida-compile {agent_ts_path} -o {AGENT_OUTPUT}"
    run_command(cmd)
    print(f"✅ Biên dịch thành công: {AGENT_OUTPUT}")



def push_libs(abi, device_id=None):
    """Push tất cả file .so trong thư mục libs/abi lên thiết bị"""
    libs_path = os.path.join(LIBS_DIR, abi)
    if not os.path.isdir(libs_path):
        print(f"❌ Thư mục không tồn tại: {libs_path}")
        sys.exit(1)

    so_files = [f for f in os.listdir(libs_path) if f.endswith(".so")]
    if not so_files:
        print(f"❌ Không tìm thấy file .so trong {libs_path}")
        sys.exit(1)

    # Tạo lệnh adb với device_id nếu có
    adb_cmd = [ADB]
    if device_id:
        adb_cmd += ["-s", device_id]

    print(f"📤 Đang push {len(so_files)} file .so đến /data/local/tmp trên thiết bị {'mặc định' if not device_id else device_id}")
    for so_file in so_files:
        src = os.path.join(libs_path, so_file)
        cmd = adb_cmd + ["push", src, "/data/local/tmp/"]
        run_command(" ".join(cmd))

    print("✅ Đã push thành công lên thiết bị!")

def remove_sourcemap(file_path):
    """Xóa dòng source map ở cuối file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Xóa dòng bắt đầu bằng //# sourceMappingURL=
    filtered_lines = [line for line in lines if not line.strip().startswith('//# sourceMappingURL=')]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(filtered_lines)

    print(f"✅ Đã xóa source map trong {file_path}")

# ================== CHÍNH ==================
def main():
    # Phân tích tham số dòng lệnh
    device_id = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "clean":
            clean()
            return
        elif sys.argv[1] == "-s" and len(sys.argv) > 2:
            device_id = sys.argv[2]
        else:
            print(f"❌ Lệnh không hợp lệ: {' '.join(sys.argv[1:])}")
            print("Sử dụng:")
            print("  python build_and_push.py                  - Build, sinh modinfo, push, biên dịch")
            print("  python build_and_push.py -s <device_id>   - Chỉ định thiết bị cụ thể (ví dụ: 127.0.0.1:5555)")
            print("  python build_and_push.py clean            - Dọn dẹp")
            sys.exit(1)

    # Nếu không chỉ định -s, dùng thiết bị mặc định
    device_id = device_id or DEFAULT_DEVICE_ID
    print(f"📱 Sử dụng thiết bị: {device_id}")

    # Kiểm tra ADB
    try:
        result = subprocess.run([ADB, "devices"], capture_output=True, text=True, check=True)
        if device_id not in result.stdout:
            print(f"❌ Thiết bị {device_id} không được kết nối hoặc không hiển thị trong 'adb devices'")
            print("Danh sách thiết bị:")
            print(result.stdout)
            sys.exit(1)
    except Exception as e:
        print("❌ ADB không hoạt động. Vui lòng:")
        print("  1. Kết nối thiết bị Android")
        print("  2. Bật USB Debugging")
        print("  3. Đảm bảo 'adb' có trong PATH")
        sys.exit(1)

    # Các bước chính
    check_ndk_path()
    build()

    abi = get_device_abi(device_id)
    if not abi:
        sys.exit(1)

    convert_so_to_ts(abi)
    push_libs(abi, device_id)
    compile_agent()
    remove_sourcemap(AGENT_OUTPUT)

    print("🎉 HOÀN TẤT: Build, sinh modinfo, push, và biên dịch _agent.js thành công!")
    print(f"➡️  Dùng _agent.js ở: {AGENT_OUTPUT}")
    print(f"📱 Đã push .so vào thiết bị: {device_id}")
    print(f"📁 Kiến trúc: {abi}")

if __name__ == "__main__":
    main()