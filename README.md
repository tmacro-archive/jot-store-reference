# Jot Server

This is the reference implementation of the Jot note API.
When built it is a single python source file with no dependencies.
Jot targets the latest python stable release, at this time, python 3.6


## API Specification

All responses from this API will be json encoded and follow this high level schema
```
	{
		"success": true|false,		# Operation exit status
		"results": null			# Operation results
	}
```
### Create a note

*	URL
	`/note`

*	Method
	`PUT`

*	Data Parameters
	*	`title` the note title
	*	`tags`	a list of tags to be added to the created note
	*	`body`	the body of the note
	
	
	Request data should be json encoded.
	All parameters are optional. 
	A empty dictionary `{}` can be used to create a blank note.
	
	Example:
	```
		{
			"title": "example",
			"tags":	["tag1", "tag2"],
			"body": "I'm an example note"
		}
		
	```
*	Success Response
	*	Code: `200`
	*	Content:
		```
			{
				"id": "3625949699dd4d8dbc03adfac35c726a",
				"title": "example",
				"tags":	["tag1", "tag2"],
				"body": "I'm an example note"
			}

		```

#### Load a note

*	URL
	`/note/<id>`

*	Method
	`GET`

*	URL Parameters
		`id`	The note id

*	Success Response
	*	Code: `200`
	*	Content: 
		```
			{
				"id": "7edb7fbc655b4a7ca8a57a7e4985dfc2", 
				"title": "example", 
				"tags": [], 
				"body": "this is an example", 
				"created": 	"2016-11-15T00:17:34.041540", 
				"modified": "2016-11-15T00:17:34.041540"
			}

		```

*	Failed Response
	*	Code: `200`
	*	Content: `{"success": false, "results": null}`

### Update a note

*	URL
	`/note`

*	Method
	`PATCH`

*	Data Parameters
	Request data should be json encoded.
	All parameters are optional. 
	Passing a empty dictionary `{}` will "touch" the note by updating it's modified timestamp
	*	`id`	the note id to update
	*	`title` the note title
	*	`tags`	a list of tags that wil be set on the note
	*	`body`	the body of the note
	
	Example:
	```
		{
			"id": "3625949699dd4d8dbc03adfac35c726a",
			"title": "example",
			"tags":	["tag1", "tag2"],
			"body": "I'm an updated note"
		}

	```

*	Success Response
	*	Code: `200`
	*	Content:
		```
			{
				"id": "3625949699dd4d8dbc03adfac35c726a",
				"title": "example",
				"tags":	["tag1", "tag2"],
				"body": "I'm an updated note"
			}
			
		```

#### Search for notes

*	URL
	`GET`

*	Query Parameters
	*	`title`
		Providing `title` will preform 
		a simple substring search on all note titles.
		Only one `title` should be used.
		If multiple are passed the first is used.
	
	*	`tags`
		Providing `tags` will select any notes with a matching tag.
		Multiple `tags` can be provided.

	*	`search`
		This parameter is currently not implemented.
		Providing `search` will preform a fuzzy text search on all note bodies.
		Multiple `search` can be passed.
		The behaviour of the search param is likely to be implementation specific 
		as libraries and algorithms will differ across codebases

	*	`limit`
		If provided the call will return at most `limit` results.


*	Success Response
	*	Code: `200`
	*	Content: 
		```
			[
				{
					"id": "7edb7fbc655b4a7ca8a57a7e4985dfc2", 
					"title": "example", 
					"tags": ["examples", "stuff"], 
					"body": "this is an example", 
					"created": 	"2016-11-15T00:17:34.041540", 
					"modified": "2016-11-15T00:17:34.041540"
				},
				{
					"id": "d2692f8263874f3a87d8a33f10e9f331", 
					"title": "another example", 
					"tags": ["examples"], 
					"body": "this is also an example",
					"created": "2017-05-01T21:58:23.589126", 
					"modified": "2017-05-01T21:58:23.589126"
				}
			]

		```

*	Failed Response
	*	Code: `200`
	*	Content: `{"success": false, "results": null}`
