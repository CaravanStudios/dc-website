// vite.config.ts
import { defineConfig } from "file:///Users/andrei/TechSoup/DataCommon/dc-website/packages/web-components/node_modules/vite/dist/node/index.js";
import typescript from "file:///Users/andrei/TechSoup/DataCommon/dc-website/packages/web-components/node_modules/@rollup/plugin-typescript/dist/es/index.js";
import path from "path";
import { typescriptPaths } from "file:///Users/andrei/TechSoup/DataCommon/dc-website/packages/web-components/node_modules/rollup-plugin-typescript-paths/dist/index.js";
var __vite_injected_original_dirname = "/Users/andrei/TechSoup/DataCommon/dc-website/packages/web-components";
var vite_config_default = defineConfig({
  plugins: [],
  resolve: {
    alias: [
      {
        find: "~",
        replacement: path.resolve(__vite_injected_original_dirname, "./src")
      }
    ]
  },
  server: {
    port: 3e3
  },
  build: {
    manifest: true,
    minify: true,
    reportCompressedSize: true,
    lib: {
      entry: path.resolve(__vite_injected_original_dirname, "src/main.ts"),
      fileName: "main",
      formats: ["es", "cjs"]
    },
    rollupOptions: {
      external: [],
      plugins: [
        typescriptPaths({
          preserveExtensions: true
        }),
        typescript({
          sourceMap: false,
          declaration: true,
          outDir: "dist"
        })
      ]
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCIvVXNlcnMvYW5kcmVpL1RlY2hTb3VwL0RhdGFDb21tb24vZGMtd2Vic2l0ZS9wYWNrYWdlcy93ZWItY29tcG9uZW50c1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiL1VzZXJzL2FuZHJlaS9UZWNoU291cC9EYXRhQ29tbW9uL2RjLXdlYnNpdGUvcGFja2FnZXMvd2ViLWNvbXBvbmVudHMvdml0ZS5jb25maWcudHNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL1VzZXJzL2FuZHJlaS9UZWNoU291cC9EYXRhQ29tbW9uL2RjLXdlYnNpdGUvcGFja2FnZXMvd2ViLWNvbXBvbmVudHMvdml0ZS5jb25maWcudHNcIjsvLyB2aXRlLmNvbmZpZy50c1xuaW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSBcInZpdGVcIjtcblxuaW1wb3J0IHR5cGVzY3JpcHQgZnJvbSBcIkByb2xsdXAvcGx1Z2luLXR5cGVzY3JpcHRcIjtcbmltcG9ydCBwYXRoIGZyb20gXCJwYXRoXCI7XG5pbXBvcnQgeyB0eXBlc2NyaXB0UGF0aHMgfSBmcm9tIFwicm9sbHVwLXBsdWdpbi10eXBlc2NyaXB0LXBhdGhzXCI7XG5cbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZyh7XG4gIHBsdWdpbnM6IFtdLFxuICByZXNvbHZlOiB7XG4gICAgYWxpYXM6IFtcbiAgICAgIHtcbiAgICAgICAgZmluZDogXCJ+XCIsXG4gICAgICAgIHJlcGxhY2VtZW50OiBwYXRoLnJlc29sdmUoX19kaXJuYW1lLCBcIi4vc3JjXCIpLFxuICAgICAgfSxcbiAgICBdLFxuICB9LFxuICBzZXJ2ZXI6IHtcbiAgICBwb3J0OiAzMDAwLFxuICB9LFxuICBidWlsZDoge1xuICAgIG1hbmlmZXN0OiB0cnVlLFxuICAgIG1pbmlmeTogdHJ1ZSxcbiAgICByZXBvcnRDb21wcmVzc2VkU2l6ZTogdHJ1ZSxcbiAgICBsaWI6IHtcbiAgICAgIGVudHJ5OiBwYXRoLnJlc29sdmUoX19kaXJuYW1lLCBcInNyYy9tYWluLnRzXCIpLFxuICAgICAgZmlsZU5hbWU6IFwibWFpblwiLFxuICAgICAgZm9ybWF0czogW1wiZXNcIiwgXCJjanNcIl0sXG4gICAgfSxcbiAgICByb2xsdXBPcHRpb25zOiB7XG4gICAgICBleHRlcm5hbDogW10sXG4gICAgICBwbHVnaW5zOiBbXG4gICAgICAgIHR5cGVzY3JpcHRQYXRocyh7XG4gICAgICAgICAgcHJlc2VydmVFeHRlbnNpb25zOiB0cnVlLFxuICAgICAgICB9KSxcbiAgICAgICAgdHlwZXNjcmlwdCh7XG4gICAgICAgICAgc291cmNlTWFwOiBmYWxzZSxcbiAgICAgICAgICBkZWNsYXJhdGlvbjogdHJ1ZSxcbiAgICAgICAgICBvdXREaXI6IFwiZGlzdFwiLFxuICAgICAgICB9KSxcbiAgICAgIF0sXG4gICAgfSxcbiAgfSxcbn0pO1xuIl0sCiAgIm1hcHBpbmdzIjogIjtBQUNBLFNBQVMsb0JBQW9CO0FBRTdCLE9BQU8sZ0JBQWdCO0FBQ3ZCLE9BQU8sVUFBVTtBQUNqQixTQUFTLHVCQUF1QjtBQUxoQyxJQUFNLG1DQUFtQztBQU96QyxJQUFPLHNCQUFRLGFBQWE7QUFBQSxFQUMxQixTQUFTLENBQUM7QUFBQSxFQUNWLFNBQVM7QUFBQSxJQUNQLE9BQU87QUFBQSxNQUNMO0FBQUEsUUFDRSxNQUFNO0FBQUEsUUFDTixhQUFhLEtBQUssUUFBUSxrQ0FBVyxPQUFPO0FBQUEsTUFDOUM7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBLEVBQ0EsUUFBUTtBQUFBLElBQ04sTUFBTTtBQUFBLEVBQ1I7QUFBQSxFQUNBLE9BQU87QUFBQSxJQUNMLFVBQVU7QUFBQSxJQUNWLFFBQVE7QUFBQSxJQUNSLHNCQUFzQjtBQUFBLElBQ3RCLEtBQUs7QUFBQSxNQUNILE9BQU8sS0FBSyxRQUFRLGtDQUFXLGFBQWE7QUFBQSxNQUM1QyxVQUFVO0FBQUEsTUFDVixTQUFTLENBQUMsTUFBTSxLQUFLO0FBQUEsSUFDdkI7QUFBQSxJQUNBLGVBQWU7QUFBQSxNQUNiLFVBQVUsQ0FBQztBQUFBLE1BQ1gsU0FBUztBQUFBLFFBQ1AsZ0JBQWdCO0FBQUEsVUFDZCxvQkFBb0I7QUFBQSxRQUN0QixDQUFDO0FBQUEsUUFDRCxXQUFXO0FBQUEsVUFDVCxXQUFXO0FBQUEsVUFDWCxhQUFhO0FBQUEsVUFDYixRQUFRO0FBQUEsUUFDVixDQUFDO0FBQUEsTUFDSDtBQUFBLElBQ0Y7QUFBQSxFQUNGO0FBQ0YsQ0FBQzsiLAogICJuYW1lcyI6IFtdCn0K
