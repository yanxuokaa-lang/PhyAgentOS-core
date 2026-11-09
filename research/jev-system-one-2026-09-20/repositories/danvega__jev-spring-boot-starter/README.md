# Jev Spring Boot Starter

Ask typed questions with [TypeSafe Jev](https://docs.typesafe.ai/introduction) from a Spring MVC application.
Add one dependency, set an API key, and inject `JevClient`.

**Spring Boot 4.0+ · Java 17+ · Spring MVC · RestClient · Jackson 3**

This is an independent community project. Version `0.1.0-SNAPSHOT` is a local development version and is not published to Maven Central.

## Get started

First, build and install the starter from this repository:

```sh
./mvnw clean install
```

Add it to an existing Spring Boot 4 MVC application:

```xml
<dependency>
    <groupId>dev.danvega</groupId>
    <artifactId>jev-spring-boot-starter</artifactId>
    <version>0.1.0-SNAPSHOT</version>
</dependency>
```

Your application supplies `spring-boot-starter-webmvc`. The Jev starter supplies
`spring-boot-starter-restclient`; it does not start a web server itself.

Set the key:

```sh
export TYPESAFE_API_KEY=your-key
```

Inject the client into a service:

```java
import dev.danvega.jev.JevClient;
import dev.danvega.jev.Question;
import org.springframework.stereotype.Service;
import java.util.Map;

@Service
public class TicketService {
    private final JevClient jev;

    public TicketService(JevClient jev) {
        this.jev = jev;
    }

    public String route(String message) {
        var response = jev.evaluate(message, Map.of(
                "team", Question.choice("Which team should handle this?",
                        "billing", "integrations", "support")));

        return response.choice("team").choice();
    }
}
```

No enable annotation or component scanning configuration is needed. The starter activates
in servlet applications, supplies one `JevClient`, and backs off when you provide your own.
It makes no HTTP calls during startup. A missing API key produces an actionable startup error.

## Three question types, one request

```java
var response = jev.evaluate("Stripe is broken and I cannot accept payments!", Map.of(
        "urgent", Question.noul("Does this need urgent attention?"),
        "team", Question.choice("Which team should handle this?", Map.of(
                "billing", "Charges and refunds",
                "integrations", "Connecting third-party services")),
        "severity", Question.score("How severe is the issue?",
                "Cosmetic", "Workaround available", "Blocking")));

double urgency = response.noul("urgent").noul();
String team = response.choice("team").choice();
double confidence = response.choice("team").confidence();
double severity = response.score("severity").score();
```

| Factory | Meaning | Result |
| --- | --- | --- |
| `Question.noul(...)` | Yes/no judgment | Probability of yes, between 0 and 1 |
| `Question.choice(...)` | Choose a named option | Label, probabilities, confidence |
| `Question.score(...)` | Rate against ordered levels | Weighted zero-based score, legend, probabilities, confidence |

A three-level score spans 0–2 and can fall between levels. Your application decides what
probability or confidence is sufficient to act; the starter does not impose thresholds.

`response.answers()` exposes the full `Map<String, Answer>`. The named accessors above
check the answer type and give a clear error for a missing name or incorrect accessor.
`response.model()` reports the actual model; `response.usage()` provides token counts.

State can be text, a record, a map, or a list that Spring's Jackson converter can serialize.
Instructions and criterion descriptions also accept structured values. Choice labels can
have null descriptions; the varargs factory handles that without a null-containing map.
Collections are shallow snapshots: treat any nested caller-owned values as immutable while in use.

To describe both sides of a yes/no question:

```java
Question.noul("Is this urgent?", "Explicitly time sensitive", "Can wait until next week");
```

To override the model for one call:

```java
import dev.danvega.jev.JevRequest;

var response = jev.evaluate(new JevRequest(message, questions, "jev-1.13.0"));
```

## Configuration

### Virtual threads on JDK 21+

Enable Spring Boot's virtual-thread support in your MVC application:

```yaml
spring:
  threads:
    virtual:
      enabled: true
```

With Boot's embedded Tomcat, MVC requests then run on virtual threads on JDK 21+.
`JevClient` and `RestClient` execute synchronously on that same request thread, allowing
blocking HTTP I/O to benefit from virtual threads. The client needs no extra executor or
asynchronous API. This helps concurrency during I/O waits; it does not make Jev inference faster.

The included example enables this setting. Boot falls back to platform threads on JDK 17;
set `spring.threads.virtual.enabled=false` to opt out on newer JDKs. The starter itself
does not change application-wide threading settings. Calls made outside MVC use their
caller's thread as usual.

See [Spring Boot virtual threads](https://docs.spring.io/spring-boot/reference/features/spring-application.html#features.spring-application.virtual-threads).

### Jev properties

| Property | Default | Purpose |
| --- | --- | --- |
| `jev.api-key` | `TYPESAFE_API_KEY` fallback | TypeSafe API key |
| `jev.base-url` | `https://api.typesafe.ai` | API root, without `/v1/systemone` |
| `jev.model` | `jev-latest` | Default model |
| `jev.enabled` | `true` | Enable auto-configuration |

These properties have generated IDE completion metadata. Spring's standard property-source
precedence applies. You can also set `JEV_API_KEY`, `JEV_BASE_URL`, and `JEV_MODEL`.
An explicitly configured `jev.api-key` wins over `TYPESAFE_API_KEY`; an explicitly blank key
is an error rather than silently selecting another credential.

For YAML-based configuration:

```yaml
jev:
  api-key: ${TYPESAFE_API_KEY}
  model: jev-latest
```

### HTTP settings

The client uses a clone of Boot's configured `RestClient.Builder`, retaining its message
converters, request factory, interceptors, and observation configuration. The starter does
not install a second JSON mapper or replace your HTTP transport.

Set timeouts using Boot 4's standard properties:

```yaml
spring:
  http:
    clients:
      connect-timeout: 5s
      read-timeout: 10s
```

These settings apply to Boot-configured HTTP clients application-wide. The starter adds
no timeout of its own; without configured values, the selected request factory's defaults apply.
Use a Spring `RestClientCustomizer` for shared interceptors or other HTTP customization.

For Jev-specific customization, supply your own bean:

```java
import dev.danvega.jev.JevClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestClient;

@Bean
JevClient jevClient(RestClient.Builder builder,
        @Value("${jev.api-key:${TYPESAFE_API_KEY:}}") String apiKey) {
    var restClient = builder.clone()
            .baseUrl("https://api.typesafe.ai")
            .defaultHeaders(headers -> headers.setBearerAuth(apiKey))
            .defaultHeader("X-Application", "support")
            .build();
    return new JevClient(restClient, "jev-latest");
}
```

Place this method in an application configuration class. When a custom `JevClient` is
present, your configuration owns its credentials and HTTP settings.

### Errors and retries

HTTP failures use Spring's `RestClientResponseException`, preserving the status, response
headers (including `Retry-After`), and body. Connection failures use `ResourceAccessException`.
Malformed responses raise `RestClientException`; missing numeric values never become zero.
Unknown JSON fields are ignored, while unknown answer types and mismatched answer names/types fail.

**The starter makes one attempt per evaluation and has no automatic retry policy.** Unlike the
JavaScript SDK, it leaves retry decisions to the application. For 429/529 responses, an application
can honor `Retry-After` and apply bounded backoff. Consider that retrying a POST after an ambiguous
timeout can repeat work. Do not configure an error handler that suppresses failed HTTP statuses.

## Run the MVC example

The [support-triage example](examples/support-triage) exposes `POST /triage`:

```sh
./mvnw install
export TYPESAFE_API_KEY=your-key
./mvnw -f examples/support-triage/pom.xml spring-boot:run
```

From another terminal:

```sh
curl http://localhost:8080/triage \
  -H 'Content-Type: application/json' \
  -d '{"message":"Stripe is broken and I cannot accept payments!"}'
```

This example calls the live API only when you send a request. Its tests use a local HTTP stub.

## Development

```sh
./mvnw clean install
./mvnw -f examples/support-triage/pom.xml clean verify
```

The compatibility matrix covers Boot 4.0.0, 4.0.8, and 4.1.1 on Java 17, 21, and 25.
The MVC test verifies the actual outgoing HTTP call runs on a virtual thread on JDK 21+,
with separate checks for the platform-thread opt-out and JDK 17 fallback.
To select a version for either build, add `-Dspring-boot.version=4.1.1`.
All tests are offline and require no API key.