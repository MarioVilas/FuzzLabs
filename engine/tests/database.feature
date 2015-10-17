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

