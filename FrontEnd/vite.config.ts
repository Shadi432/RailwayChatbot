// import { defineConfig } from 'vite'
// import react from '@vitejs/plugin-react-swc'
//
//
// // https://vite.dev/config/
// export default defineConfig({
//   plugins: [react()],
// })

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // (optional) explicitly set your front-end port
    port: 5173,
    proxy: {
      // Proxy any call from the browser to /chatbot → http://localhost:5000/chatbot
      "/chatbot": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
      // And proxy /tickets/* → http://localhost:5000/tickets/*
      "/tickets": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
});
