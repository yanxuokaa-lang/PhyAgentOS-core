# TypeSafe AI Go SDK (unofficial)

Unofficial Go SDK for [TypeSafe AI](https://typesafe.ai) and its Jev API. Abstractions kept very minimal.

## Quickstart

Install the SDK (Go 1.26 or newer):

```sh
go get github.com/guillemus/jev-go
```

Set `TYPESAFE_API_KEY` in your environment, then create and use the client:

```go
package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/guillemus/jev-go"
)

func main() {
	client := jev.NewClient(os.Getenv("TYPESAFE_API_KEY"))
	response, err := client.SystemOne(context.Background(), jev.Request{
		State: map[string]string{
			"document": "I was charged twice. Please fix this ASAP.",
		},
		Questions: map[string]jev.Question{
			"category": jev.Choice("What is this ticket about?", map[string]any{
				"billing":   nil,
				"technical": nil,
				"other":     nil,
			}),
		},
	})
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println(response.Answers["category"].Choice)
}
```

Supports Noul, Choice, Score, structured inputs, and model listing.
Use `jev.NewClientWithConfig` for custom settings.

## Documentation

Learn what TypeSafe can do in the [TypeSafe docs](https://docs.typesafe.ai).
See the [examples](examples/README.md) for usage and the
[Go API reference](https://pkg.go.dev/github.com/guillemus/jev-go) for client types and options.
