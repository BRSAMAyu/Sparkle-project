/*
 * FIX-559: Swagger UI 初始化脚本（外置化）。
 *
 * 上游 FastAPI 模板以页面内联 <script> 初始化 SwaggerUIBundle，被本应用
 * CSP（script-src 'self'）拦截。此处将执行逻辑移入同源静态文件，序列化
 * 参数从页面 <script type="application/json" id="swagger-init-config">
 * 数据块读取（数据块非执行型，不受 script-src 约束）。
 * 镜像 fastapi.openapi.docs.swagger_ui_default_parameters 的默认项；
 * presets 无法 JSON 序列化，在此以对象形式补齐。
 */
window.addEventListener('load', function () {
  var configEl = document.getElementById('swagger-init-config');
  if (!configEl || typeof SwaggerUIBundle === 'undefined') {
    return;
  }
  var config = JSON.parse(configEl.textContent || '{}');
  if (config.oauth2RedirectPath) {
    config.oauth2RedirectUrl = window.location.origin + config.oauth2RedirectPath;
    delete config.oauth2RedirectPath;
  }
  config.presets = [
    SwaggerUIBundle.presets.apis,
    SwaggerUIBundle.SwaggerUIStandalonePreset,
  ];
  window.ui = SwaggerUIBundle(config);
});
