import com.intuit.karate.junit5.Karate;

class AnalysisEditorRunner {

    @Karate.Test
    Karate testAnalysisEditor() {
        return Karate.run("classpath:analyses/analysis-editor.feature").relativeTo(getClass());
    }
}
