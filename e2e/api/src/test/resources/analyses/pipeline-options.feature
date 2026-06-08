@regression
Feature: Analysis with different pipeline options (data-driven)

  Background:
    * url baseUrl

  Scenario Outline: Analysis completes with <description>
    # Upload — medium.pdf (not small.pdf) because docling-serve cpu v1.21.0
    # 404s on 1-page PDFs through this pipeline (upstream issue #466) and
    # the enrichment scenarios below need more than one page of content to
    # exercise the code/formula models without producing empty results.
    * def uploaded = call read('classpath:common/helpers/upload.feature') { file: 'medium.pdf' }

    # Create analysis with specific options
    Given path '/api/analyses'
    And request { documentId: '#(uploaded.docId)', pipelineOptions: #(options) }
    When method POST
    Then status 200
    * def jobId = response.id

    # Poll until terminal state
    Given path '/api/analyses', jobId
    And retry until response.status == 'COMPLETED' || response.status == 'FAILED'
    When method GET
    Then status 200
    And match response.status == 'COMPLETED'
    And match response.contentMarkdown == '#string'

    # Cleanup
    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(uploaded.docId)' }

    Examples:
      | read('classpath:common/data/test-cases/pipeline-options.json') |
