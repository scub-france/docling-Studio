import com.intuit.karate.junit5.Karate;

/**
 * Runner for the demo capture scenario — deliberately separate from UIRunner.
 *
 * demo/ask-demo.feature is not a test: it drives the browser for a video
 * recording and asserts almost nothing. UIRunner must never pick it up, which
 * is why it lives outside the classpath roots UIRunner scans and carries @demo.
 *
 * Needs a running backend (REASONING_ENABLED=true + warm Ollama) and frontend.
 * See scripts/demo/README.md — this is normally invoked by scripts/demo/record.sh,
 * not by hand.
 */
class DemoRunner {

    @Karate.Test
    Karate demo() {
        return Karate.run("classpath:demo").tags("@demo").relativeTo(getClass());
    }
}
