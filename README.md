  ## About this project

  - This project is deployed as a telegrams bot
  - The bot gives you list of available sheet names
    - It gives the unique sheet_name attribute value available in the topics MongoDB collection
  - You can choose any of the given sheet name
  - The bot would do a left join on topics collection and history collections to give you the topics for the given sheet_name which haven't been already seen
  - The bot would then randomly select a topic from the unseen list and give it's details along with a google search link to read more about the topic
  - It also updates the history table to add the new selected topic
  - It also asks if you want to mark the topic for revision. If yes, then in removes the topic from the history