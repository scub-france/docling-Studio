@ignore
Feature: Helper — Upload a PDF via the UI

  # Callable feature: uploads a file through the browser file input
  # Usage: * call read('classpath:common/helpers/ui-upload.feature') { file: 'small.pdf' }
  # Prerequisite: driver must already be on a page with .upload-zone (home or studio)

  Scenario:
    * driver.inputFile('input[type=file]', 'classpath:common/data/generated/' + file)
