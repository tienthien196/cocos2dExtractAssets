// src/server.ts

import express from 'express';
import path from 'path';
import fs from 'fs';
import { app_name } from './common';
import { connect_frida } from './utils';

const app = express();
const port = 3000;

// 🔧 Xác định đường dẫn đến _agent.js
// Cấu trúc dự kiến: cocos2dExtractAssets/ -> frida/_agent.js, web/src/server.ts
const fridaScriptFile = path.join(__dirname, '..', '..', 'frida', '_agent.js');

// ✅ Kiểm tra file tồn tại trước khi dùng
console.log('🔍 Đang kiểm tra đường dẫn _agent.js...');
console.log('📁 Đường dẫn:', fridaScriptFile);

if (!fs.existsSync(fridaScriptFile)) {
  console.error(`❌ Lỗi: Không tìm thấy file _agent.js tại: ${fridaScriptFile}`);
  console.error('💡 Hãy đảm bảo:');
  console.error('   1. Bạn đã chạy build_and_push.py thành công');
  console.error('   2. File _agent.js nằm trong thư mục ../frida/');
  console.error('   3. Bạn đang chạy server từ thư mục web/');
  process.exit(1);
}

console.log('✅ File _agent.js đã được tìm thấy');

// Serve static files (web UI)
app.use(express.static(path.join(__dirname, '..', 'dist', 'public')));
app.use(express.json());

// ✅ Biến global để lưu script
let fridaScript: any = null;

// ✅ Gọi connect_frida, nhưng luôn tạo route
connect_frida(
  app_name,
  fridaScriptFile,
  (script) => {
    fridaScript = script;
    if (script) {
      console.log('✅ Frida script đã được load và sẵn sàng');
    } else {
      console.warn('⚠️  Frida script load thất bại. Route vẫn hoạt động, nhưng không thể gọi hàm');
    }
  },
  (message) => {
    console.log('📡 Frida message:', message);
  }
);

// ✅ Route luôn tồn tại, dù Frida có lỗi
app.post('/api/invoke_frida_function', async (req, res) => {
  const { fun, arg } = req.body;

  if (!fridaScript) {
    console.warn('🚫 Không thể gọi hàm: Frida script chưa sẵn sàng');
    return res.status(503).json({
      error: 'Frida chưa kết nối. Vui lòng kiểm tra:',
      details: [
        '1. Đã chạy frida-server trên thiết bị',
        '2. Game đang chạy',
        '3. File _agent.js tồn tại và hợp lệ',
        '4. Không có lỗi trong log server'
      ]
    });
  }

  try {
    console.log(`📞 Đang gọi hàm: ${fun}`);
    const result = await fridaScript.exports.invoke_frida_function(fun, arg);
    
    if (result instanceof Buffer || result instanceof ArrayBuffer) {
      res.setHeader('Content-Type', 'application/octet-stream');
      return res.send(result);
    }
    
    console.log('✅ Gọi hàm thành công');
    res.json(result);
  } catch (error: any) {
    console.error('❌ Lỗi khi gọi hàm Frida:', error);
    res.status(500).json({ 
      error: error.message,
      stack: error.stack 
    });
  }
});

// ✅ Bắt đầu server
app.listen(port, () => {
  console.log(`🚀 Server đang chạy tại http://localhost:${port}`);
  console.log(`📁 Đang phục vụ từ: ${path.join(__dirname, '..', 'dist', 'public')}`);
  console.log(`📱 Đang kết nối đến ứng dụng: ${app_name}`);
});

// ✅ Gợi ý: Dùng lệnh này để test API
console.log(`💡 Dùng curl để test:\n   curl -X POST http://localhost:3000/api/invoke_frida_function -H "Content-Type: application/json" -d '{"fun":"getAssetsList","arg":[]}'`);