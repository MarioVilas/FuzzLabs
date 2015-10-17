Feature: database handling

  Scenario: saving session status data
      Given we have session status data
       When we save the session status data
       Then true is returned if session data was saved

  Scenario: loading session status data
      Given we are connected to the database
       When we load the session status data
       Then the session data is returned

  Scenario: updating session status data
      Given we are connected to the database
       When we update the session status data
       Then true is returned if update was successful

  Scenario: deleting session status data
      Given we are connected to the database
       When we delete the session status data
       Then true is returned if the session data was deleted

  Scenario: retrieve list of jobs
      Given we are connected to the database
       When we retrieve the list of jobs
       Then a job list is returned

  Scenario: insert a job into the database
      Given we are connected to the database
       When we insert a job into the database
       Then true is returned if job was saved

  Scenario: load the job from the database
      Given we are connected to the database
       When we load the job from the database
       Then the job description is returned

  Scenario: update a job in the database
      Given we are connected to the database
       When we update a job in the database
       Then true is returned if job was updated

  Scenario: delete a job in the database
      Given we are connected to the database
       When we delete a job in the database
       Then true is returned if job was deleted

  Scenario: insert an issue into the database
      Given we are connected to the database
       When we insert an issue into the database
       Then the issue ID is returned if the issue was saved

  Scenario: load the issue from the database
      Given we are connected to the database
       When we load the issue from the database
       Then the issue dictionary is returned

  Scenario: load the list of issues from the database
      Given we are connected to the database
       When we load the list of issues from the database
       Then a list of issues is returned

  Scenario: delete the issues from the database
      Given we are connected to the database
       When we delete the issue from the database
       Then true is returned if the issue was deleted

  Scenario: log events to the database
      Given we are connected to the database
       When we log several events to the database
       Then true is returned if the events were logged

  Scenario: read logs from database
      Given we are connected to the database
       When we fetch the list of logs from database
       Then a list of logs is returned

  Scenario: read logs from database from a given time
      Given we are connected to the database
       When we get logs newer than timestamp from database
       Then a list of logs newer than timestamp is returned

