// src/utils.ts

import * as frida from 'frida';
import * as fs from 'fs';

export const connect_frida = async (
  app_name: string,
  fridaScriptFile: string,
  init_cb: (script: frida.Script | null) => void, // ✅ Bắt buộc, không optional
  message_cb?: (message: any) => void
) => {
  try {
    const device = await frida.getUsbDevice();
    console.log('✅ Connected to device:', device.name);

    const processes = await device.enumerateProcesses();
    const targetProcess = processes.find(p => p.name === app_name || p.name.includes(app_name));

    if (!targetProcess) {
      console.error(`❌ Không tìm thấy process: ${app_name}`);
      console.log('Các process đang chạy:');
      processes.forEach(p => console.log(`  ${p.pid} ${p.name}`));
      init_cb(null); // ✅ Vẫn gọi callback
      return;
    }

    const session = await device.attach(targetProcess.pid);
    console.log(`✅ Đã attach vào: ${targetProcess.name} (PID: ${targetProcess.pid})`);

    const scriptContent = fs.readFileSync(fridaScriptFile, 'utf8');
    const script = await session.createScript(scriptContent);

    script.message.connect((message) => {
      message_cb?.(message);
    });

    await script.load();
    console.log('✅ Frida script đã được load');

    init_cb(script); // ✅ Gọi với script thành công
  } catch (error) {
    console.error('❌ Lỗi kết nối Frida:', error);
    init_cb(null); // ✅ Vẫn gọi callback dù thất bại
  }
};