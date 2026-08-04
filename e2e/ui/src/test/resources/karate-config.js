function fn() {
  var config = {
    baseUrl: karate.properties['baseUrl'] || 'http://localhost:8000',
    uiBaseUrl: karate.properties['uiBaseUrl'] || 'http://localhost:3000',
    pollInterval: 2000,
    pollTimeout: 120000,
    batchPollTimeout: 300000
  };
  karate.configure('connectTimeout', 10000);
  karate.configure('readTimeout', 30000);
  karate.configure('retry', { count: 60, interval: config.pollInterval });

  // Karate UI — browser driver config (Chrome headless)
  karate.configure('driver', {
    type: 'chrome',
    headless: true,
    showDriverLog: false,
    addOptions: ['--no-sandbox', '--disable-gpu'],
    screenshotOnFailure: true
  });

  // Demo capture mode (-Ddemo=true) — a visible Chrome at a fixed geometry so
  // ffmpeg can crop the same rectangle on every take. Only demo/ask-demo.feature
  // runs this way; the test suite above is untouched. See scripts/demo/README.md.
  if (karate.properties['demo'] === 'true') {
    config.demoWindow = { width: 1440, height: 900 };
    karate.configure('driver', {
      type: 'chrome',
      headless: false,
      showDriverLog: false,
      addOptions: [
        '--window-size=1440,900',
        '--window-position=0,0',
        '--hide-crash-restore-bubble',
        '--disable-infobars',
        '--disable-session-crashed-bubble',
        '--disable-features=TranslateUI',
        '--autoplay-policy=no-user-gesture-required'
      ],
      screenshotOnFailure: true
    });
  }

  return config;
}
