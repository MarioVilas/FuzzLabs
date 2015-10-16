Feature: saving and loading issue data

  Scenario: no issues in database
      Given we have root and config and no issues
       When we load the list of issues
       Then we receive a list without issues

  Scenario: no issues in database
      Given we have root and config and no issues
       When we load an issue
       Then we receive an empty dictionary without issue data

  Scenario: no issues in database
      Given we have root and config and no issues
       When we delete an issue
       Then we receive False as the issue was not found

  Scenario: save an issue to the database
      Given we have root, config and issue data
       When we save an issue
       Then we receive True

  Scenario: get list of issues from database
      Given we have root directory and configuration
       When we load the list of issues
       Then we receive a list of dictionaries

  Scenario: get an issue from database
      Given we have root directory and configuration
       When we load an issue
       Then we receive a dictionary with issue data

  Scenario: delete an issue from database
      Given we have root directory and configuration
       When we delete an issue
       Then we receive True if issue was deleted

  Scenario: save a job to the database
      Given we have root, config and job data
       When we save a job
       Then we receive True if the job was saved

  Scenario: delete a job from the database
      Given we have root, config and job id
       When we delete a job
       Then we receive True if the job was deleted

