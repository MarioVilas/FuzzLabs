Feature: session status handling

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

