# Metro Nyam
**Short description **
Search and find restaurants and bars in Barcelona using MetroNyam. 

## Getting Started
### Prerequisites
* [Python](https://www.python.org/) is required, version 3.9 or older is recommended.
* A [Telegram](https://telegram.org/) account is required to use the bot.



### Installation
Use the package manaker [pip](https://pip.pypa.io/en/stable/) to install the required packages, which can be found in the requirements file.
```bash
pip install -r requirements.txt

```
### Usage
NyamBot can be used through the Telegram messaging app. Search for *@AP2_Nyam_Bot* or click the following [link](https://t.me/AP2_nyam_bot).

The bot offers the following commands

- `/start`: starts the conversation.
- `/help`: shows help about the available commands and options.
- `/options`: customize bot options. The following options are available: *accessibility*.
- `/author:` shows info about the authors of the project.
- `/find <query>` searchs for restaurants which satisfy the query and shows up to 12 results sorted by distance. 
    - Search queries can be composed of multiples words such as "Pizzeria Sants". The `/find` command will find restaurants which are a result to all the words in the query.
    - Logical expressions can be used.  The supported operators are `and`, `or` and `not`. Queries are in preorder format. An example is 
    `/find and(frankfurt,and(Pedralbes,not(Sants)))`.
- `/info <number>` show additional information about a restaurant, specifying the number which is showed in the results when using `/find`.
- `/guide <number>` show a map and information of the shortest path from your location to the specified restaurant. Use the number which appears next to the restaurant in the last usage of `/find <query>`. The bot must have received your location.
- `/accessibility` toggles the accessibility setting (false by default). If accessibility is enabled the bot will guide you through an accessible plath to the restaurant.
- `/plot_metro` Plot in an image the metro network of Barcelona.


## Contributing

## License

## Authors

