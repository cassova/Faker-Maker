# Faker-Maker
This module creates fake pandas dataframes using a IPython magic function with custom domain specific language.

## Example usage
```
%%fakedata seed=2, lang=jp_JP
# This is an improved version that supports comments
persons {10}
-----------------------
first_name  #This is a comment
last_name*  #Every lastname in the dataset will be unique
phone_number
#test('first',2=2,third=3,4)
random_number(digits=5) as customer_number [1]*

purchases     # I've also improved it to include an optional size
---------
isbn10
credit_card_full
random_number(digits=3) as price
random_number(digits=5) as customer_number [1,2]  # this reference says it's a child of persons and parent of comments

comments {2000}
---------
text(max_nb_chars=280) as comment
random_number(digits=5) as customer_number [2]
```
See also example.ipynb

## The `FakeDataFrameBuilder` class
The heavy lifter for this assignment is named `FakeDataFrameBuilder`.  It resides in the file `faker_maker.py`.  It is designed to be used as the magic function `%%fakedata` which is demonstrated in this notebook.  Using it as a class instead of a magic function is also possible.  Create an instance of it as such:
```
from faker_maker import FakeDataFrameBuilder
cls = FakeDataFrameBuilder(text)
```
Where `text` is the multi-line text blob containing one or more dataframe definitions.  The worker function that parses the text blob and builds the dataframes is `parse` and is called like this:
```
cls.parse()
```
Access the results within the variable `dataframes`.  Since multiple dataframes might be built, this object is a dictionary of each dataframe indexed by the name.
```
persons = cls.dataframes['persons']
```
Below are a few notes on the structure and operation that may differ from the request and provide more clarity.

## An attempt at a more formal grammar

```
function_to_call  ::= <wordcharacters>
parameters        ::= "" | "(" ( wordcharacters | number ) ")"
as_name           ::= "" | "as" <whitespace> <wordcharacters>
column_name       ::= as_name | function_to_call
reference         ::= "" |  "[" number1, number2 "]"
unique_mark       ::= "" | "*"
column_definition ::= <function_to_call> <parameters> <whitespace> \
                      <as_name> <whitespace> <reference> <unique_mark>
df_sep            ::= "--" ("-"*)
df_definition     ::= <wordcharacters> <newline> <df_sep> <newline> \
                      (<column_definition>*) <newline> <newline>
language_spec     ::= <def_definition>*
```
Source: Prof. Christopher Brooks (brooksch@umich.edu)

### Table Definitions
The table defintion has been expanded from the request to include a row count.  The default remains `99` records if no row is provided but now a new value can be specified using the special syntax ` {#}` after the table name.  For example: 

```
purchases {30}
--------------
```

If tables are to have parent-child relationships and linked by a reference (see below), then the parent defintion should be provided first and the children after.

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
```
random_number(digits=5) as customer_number
```

### References
This was expanded to allow for a comma delimited list of references and is demonstrated below.  The purpose is in the case that you want to drill down into a narrower and narrower set of values.  In the example below, not all persons will have purchases and not all purchases will have comments.  But, all comments should have one or more purchases and all purchases should have one person (since customer_number is unique on persons).  Here's how this would look:

```
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
 
### Conclusion
This was created by Nicholas Miller (nmill@umich.edu) from designs provided above by Prof. Christopher Brooks (brooksch@umich.edu).  Submitted 2020-09-23.
