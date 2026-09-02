@regression
Feature: Document upload validation

  Background:
    * url baseUrl
    * def docSchema = read('classpath:common/data/schemas/document.json')

  Scenario: Upload valid single-page PDF
    Given path '/api/documents/upload'
    And multipart file file = { read: 'classpath:common/data/generated/small.pdf', filename: 'small.pdf', contentType: 'application/pdf' }
    When method POST
    Then status 200
    And match response contains docSchema
    And match response.filename == 'small.pdf'
    And match response.pageCount == 1
    And match response.fileSize == '#? _ > 0'
    # Cleanup
    * def docId = response.id
    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(docId)' }

  Scenario: Upload valid multi-page PDF
    Given path '/api/documents/upload'
    And multipart file file = { read: 'classpath:common/data/generated/medium.pdf', filename: 'medium.pdf', contentType: 'application/pdf' }
    When method POST
    Then status 200
    And match response.pageCount == 5
    # Cleanup
    * def docId = response.id
    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(docId)' }

  Scenario: Upload valid DOCX document
    Given path '/api/documents/upload'
    And multipart file file = { read: 'classpath:common/data/generated/small.docx', filename: 'small.docx', contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }
    When method POST
    Then status 200
    And match response contains docSchema
    And match response.filename == 'small.docx'
    # Cleanup
    * def docId = response.id
    * call read('classpath:common/helpers/cleanup.feature') { docId: '#(docId)' }

  Scenario: Reject unsupported file format
    Given path '/api/documents/upload'
    And multipart file file = { read: 'classpath:common/data/generated/not-a-pdf.txt', filename: 'not-a-pdf.txt', contentType: 'text/plain' }
    When method POST
    Then status 400
    And match response.detail contains 'PDF'

  Scenario: Reject upload without file
    Given path '/api/documents/upload'
    When method POST
    Then status 422
