# Faker-Maker
This module creates pandas dataframes filled with fake data from the `Faker` package using an IPython magic function with custom domain specific language.

## Installation
`pip install fakermaker`

## Example usage

```Python
import fakermaker
```
Load the magic function
```Python
%load_ext fakermaker
```
In a separate cell, use the magic funcion `fakermaker` along with a cell filled with only the "faker-maker language".
```Python
%%fakermaker seed=0, lang=en_US
# This will create 3 pandas dataframes: persons, purchases and comments
persons {10}
-----------------------
first_name  #This is the Faker.first_name function which generates fake names
last_name*  #Every lastname in this dataset will be unique
phone_number
random_number(digits=5) as customer_number [1]* #The customer number in this dataset will be reused in purchases

purchases
---------
isbn10
credit_card_full
random_number(digits=3) as price
random_number(digits=5) as customer_number [1,2]  # this reference says it's a child of persons and parent of comments

comments {2000} # This dataset will have 2000 rows (default = 99)
---------
text(max_nb_chars=280) as comment
random_number(digits=5) as customer_number [2]
```

See also <a href='./example_usage.ipynb'>example_usage.ipynb</a>

## Faker-Maker Language

- `#` - Everything after `#` will be considered a comment and thus ignored.  *optional*
- *name* - Name of the Pandas Dataframe to create *required*
  - `{n}` - Where `n` is the number of rows in the Dataframe.  [Default=99]  *optional*
  - `#` - Everything after `#` will be considered a comment and thus ignored.  *optional*
- `--` - Header/Details divider.  Two or more `-` *required*
- `column_name` - Name of the column to add to the Pandas Dataframe. One field per line.  At least one required.  Name must match a valid `Faker` function.  See <a href='https://faker.readthedocs.io/en/master/'>Faker Documentation</a> for more details.  Column name will be the same as the function name unless you use the `as` keyword. *required*
  - `(params)` - Additional Parameters to pass the `Faker` function.  Requires key-value pairs. Read more below. *optional*
  - `*` - Requires each row in the dataframe to have a unique value for this column.  Read more below.  *optional*
  - ` as `*alias*  - Column name override. *optional*
  - `[i,j,...]` - Define references (i.e. parent/child relationship) between multiple Pandas Dataframes.  Read more below.  *optional*
  - `#` - Everything after `#` will be considered a comment and thus ignored.  *optional*
- `\n` - An additional new-line is required between dataframes.  Not required for last.  *required*

Initial version created by Prof. Christopher Brooks (brooksch@umich.edu) and improved by package author Nicholas Miller.


### Comments
The domain specific language invented for this problem was expanded to support comments similar to python using a `#`.  Comments are not supported throughout.  Examples where comments can be added:
 - After a table name (and optional row count)
 - After a field defintion
 - Before a field defintion (to comment out the field)


### Unique Values
The "unique" constraint is a bit ambiguous because let's say you have 2 columns (fields) that are defined as being unique within a dataset like in the example that was provided.  This could be interpreted in two ways: 

 1. The combination of the 2 values must be unique within the dataset
 2. Every value in the column must be unique
 
For this implementation, I found that the latter is more flexible in that it satisifies both of these points.  However, this comes with caveats that should be noted. The most obvious is a limitation of values.  For example, if you specify a column to contain a random number of length 2 and also unique, it is impossible to have a dataset with over 100 unique entries.  In fact, in how this is implemented, it is likely it would throw an exception much earlier due to how we limit the number times we look for a unique value.  Since we're using Faker to generate unique values, it should be kept in mind that there will be some limit to the number of unique values for each function.  For example, `last_name` might only generate 100 unique last names.  In my tests, I was getting duplicate values quite early on so its possible a unique set of last_names may randomly throw an error for a set of 99 unique last names.  It is recommeneded to read the Faker documentation for more information on what the limitations of each function are if you start getting errors about 'Maxed out unique checks'.

 - Future enhancement: Create a solution to #1 above.
 
### Parameters
All parameters must define the varable they are referencing in the parameter list.  This is necessary for how the parameter dictionary structure is built.  It's also good practice because it makes the parameter purpose much clearer.  For example:
```Python
random_number(digits=5) as customer_number
```

### References (i.e. Parent/Child Relationship)
If tables are to have parent-child relationships and linked by a reference, then the parent defintion should be provided first and the children after.  See the example.

This allows for a single refernce or a comma delimited list of references and is demonstrated below.  The purpose is in the case that you want to drill down into a narrower and narrower set of values.  In the example below, not all persons will have purchases and not all purchases will have comments.  But, all comments should have one or more purchases and all purchases should have one person (since customer_number is unique on persons).  Here's how this would look:

```Python
persons
-------
random_number(digits=5) as customer_number [1]*
<other fields...>

purchases
-------
random_number(digits=5) as customer_number [1,2]
<other fields...>

comments
-------
random_number(digits=5) as customer_number [2]
<other fields...>
```

NOTE: The `function_name` is not actually used on child tables since the values are actually retrieved from the parent table.  In the above example, `purchases` and `comments` all get their values from `persons` so the `random_number(digits=5)` is actually not used or validated against.
 
### Repeat Data (Goal = 25% Duplicates)
This touches on the same vain as unique since we're doing some manual tricks to try to meet this 25% goal.  The solution I chose for this is to generate 75% of the values (note: this is controlled by the field `FakeDataFrameBuilder.repeat_threshold`) from Faker.  It then analyzes the uniqueness of the results.  If 25% or more duplicates already result, we just hit up the Faker for the remaining 25% (i.e. tough luck, go look at the other guy).  If it's >0% but <25%, then we salt it by hitting up the Faker again.

For example, if the uniqueness value comes back as 20% duplicates in the first 75% generated, it's pretty safe to say that the Faker is already doing a good job at getting close to our 25% limit.  So we'll get 20% more values from the faker.

For the remaining percent (or 25% if there were no unique values), we randomly sample from within our generated list.  This will obviously result in duplicates or possibly even triplicates or more.


### Seeding
I wanted a method to regenerate the same dataset so I implemented a `seed()` function.  This generally works but doesn't seem to work well with my random_number() generator for customer_number yet.  Still need to figure that one out...

 - Issue - `seed()` still generates random customer_numbers

The seed can now be set on the magic function call line using the syntax `seed=0`.

### Language
The language can also be defined on the magic function line using the syntax `lang=jp_JP`.
