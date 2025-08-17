// src/server.ts

import express from 'express';
import path from 'path';
import { app_name } from './common';
import { connect_frida } from './utils';

const app = express();
const port = 3000;
const fridaScriptFile = path.join(__dirname, '..', 'frida', '_agent.js');

// Serve static files
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
    console.log(script ? '✅ Frida script loaded' : '⚠️ Frida script load thất bại');
  },
  (message) => {
    console.log('Frida message:', message);
  }
);

// ✅ Route luôn tồn tại
app.post('/api/invoke_frida_function', async (req, res) => {
  const { fun, arg } = req.body;

  if (!fridaScript) {
    return res.status(503).json({
      error: 'Frida chưa kết nối. Kiểm tra app có đang chạy không.'
    });
  }

  try {
    const result = await fridaScript.exports.invoke_frida_function(fun, arg);
    if (result instanceof Buffer) {
      res.setHeader('Content-Type', 'application/octet-stream');
      return res.send(result);
    }
    res.json(result);
  } catch (error: any) {
    console.error('❌ Lỗi khi gọi hàm Frida:', error);
    res.status(500).json({ error: error.message });
  }
});

app.listen(port, () => {
  console.log(`🚀 Server đang chạy tại http://localhost:${port}`);
});