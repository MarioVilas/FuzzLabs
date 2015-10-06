Feature: archive handler module

  Scenario: get archive handler descriptor
      Given we have the archive handler initialized
       When we call the archive handler descriptor
       Then we get the archive handler module descriptor

  Scenario: the archive handler is not running
      Given we have the archive handler initialized
       When we retrieve the running status
       Then we receive False as archive handler not running

  Scenario: load archived job data
      Given we have the archive handler initialized
       When we load the archived job data
       Then we get a dictionary of job details

  Scenario: get list of archived jobs
      Given we have the archive handler initialized
       When we ask for the list of archived jobs
       Then we get a list of archived jobs

