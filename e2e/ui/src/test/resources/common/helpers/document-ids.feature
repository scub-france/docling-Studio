@ignore
Feature: Helper — Ids of the documents with a given filename

  # Callable feature: returns { ids }, newest first
  # Usage: * def found = call read('classpath:common/helpers/document-ids.feature') { filename: 'small.pdf' }
  # Call it before and after an upload through the UI: the id only in the
  # second list is the uploaded document, whatever an earlier run left behind.

  Scenario:
    Given url baseUrl
    And path '/api/documents'
    When method GET
    Then status 200
    * def named = karate.filter(response, function(d){ return d.filename == filename })
    * def ids = karate.map(named, function(d){ return d.id })
