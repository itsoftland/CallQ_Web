(function () {
    const config = document.getElementById('base-config');
    if (config) {
        window.STATIC_BASE = config.dataset.staticBase;
        window.PROJECT_NAME = config.dataset.projectName;
        window.PROJECT_DISPLAY_NAME = config.dataset.projectDisplayName;
        window.APP_VERSION = config.dataset.appVersion;
    }
})();
