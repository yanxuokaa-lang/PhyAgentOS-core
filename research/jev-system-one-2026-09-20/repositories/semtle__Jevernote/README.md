# Jevernote
Console client for evernote written in Java, with git-like usage.

## What?

Jevernote is the bridge between evernote and your file system (but can be simply used with some other "services"). Evernote notebooks are represented by so-called "packages", each note is in jevernote called simply "item". On the other hand, package is represented by folder in file system as well as the item is just simply text file.

Jevernote implements sychronisation between theese two "storages". And, to be familliar with developpers, uses mechanism simillar to git. So, there are init and clone commands to initialize and push, pull, synchronize and status to transfer data between your "local storage" (file system) and "remote one" (evernote servers). 

## Build
To build, simply clone, build (using maven) and, set up an alias (not required, but preferred).

    $ clone https://github.com/martlin2cz/Jevernote
    $ cd jevernote
    $ mvn clean package
    $ alias jevernote="java -jar target/Jevernote-0.3-jar-with-dependencies.jar"

## Sample usage
To run jevernote you need __evernote authorisation token__. It is some string containing key-valued informations and for developpers can be found [here](https://www.evernote.com/api/DeveloperToken.action). Access to app for real users is in progress.

Once you have generated token, you can clone your notebooks (assuming having notebooks `foo` and `bar` and note `Lorem Ipsum` in `foo`):

    $ mkdir jevernote-test
    $ cd jevernote-test
    $ jevernote --verbose clone "<AUTH TOKEN GOES HERE>"
    INFO  Has to be done (at local):
    	create foo
    	create bar
    	create foo/Lorem Ipsum
     
    INFO  Created package foo 
    INFO  Created package bar 
    INFO  Created item Lorem Ipsum 
    
When you create new item (note), you can push it to the evernote:

    $ echo "Hello, world!" > foo/Hello
    $ jevernote --verbose status
    WARN  No record for item foo/Hello in index file 
    INFO  Changes between local and remote:
    	create foo/Hello
    $ jevernote --verbose push
    WARN  No record for item foo/Hello in index file 
    INFO  Has to be done (at remote):
    	create foo/Hello
    
    INFO  Created item Hello 
      
And the note Hello with text "Hello world!" should occur in notebook "foo" online.


## Other features

 - `--verbose` and `--debug` run
 - `--dry-run` and `--interactive`
 - `--weak` and `--force` operations
 - alike the git, `.jevernoteignore` file
 - `--save` (with backup before override)

To see other possibilities of jevernote, run with `--help` flag.

## For developpers

By implementing your custom `BaseStorage` (take a look into some existing base implementations for help) class you can create your own storage (i.e. to Dropbox, to SQL DB, to single XML file, ...). Just particullary modify the `ConsoleDataProcessor#createLocal` or `ConsoleDataProcessor#createRemote` methods to use it. 

## Anything?

Well, exactly. There is still lot of work to be done. For example

 - [ ] more precise logging, dry run and save
 - [ ] add more commands (alike local one's)
 - [x] SOLVE epicfail with items pulled from remote (no ID assigned to them, looks like mysteriously created whole new items)
 - [ ] make it more familliar (error messages)
 - [ ] production release (add OAuth)
 - [ ] conflict resolver?
 - [ ] avoid using index in FileSystem...
 - [ ] __TEST IT!!!__
