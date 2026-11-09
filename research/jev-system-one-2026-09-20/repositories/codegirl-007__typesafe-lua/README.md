# typesafe-sdk

LuaJIT client for [TypeSafe](https://typesafe.ai). You send text (or a table) and some questions. You get structured answers back.

You need LuaJIT, [LuaRocks](https://luarocks.org/), and a key from [console.typesafe.ai](https://console.typesafe.ai/settings/keys).

```sh
luarocks install typesafe-sdk
export TYPESAFE_API_KEY="sk-..."
```

```lua
local typesafe = require("typesafe")

local client, err = typesafe.new()
if not client then
  error(err.message)
end

local response, err = client:system_one({
  state = { document = "I was charged twice. Please fix this ASAP." },
  questions = {
    category = typesafe.choice("What is this ticket about?", {
      billing = "Payment or subscription issues",
      technical = "Bugs or integration problems",
      other = "Anything else",
    }),
    urgent = typesafe.noul("The message conveys urgency"),
  },
})
if not response then
  error(err.message)
end

print(response.answers.category.choice)
```

On failure you get `nil, err`. `err.code` is a short name (`unauthorized`, `rate_limited`, `timeout`, `connection`, `config`). `tostring(err)` is the message.

## Questions

- `choice(prompt, options)`: pick one label. Options is a map of label to description, not a list.
- `noul(prompt)`: how likely the answer is yes, from 0 to 1.
- `score(prompt, levels)`: rate against an ordered list. You need at least two levels.

`client:models()` lists the models your key can use.

## Config

`TYPESAFE_API_KEY` is required. You can also set `TYPESAFE_BASE_URL`, `TYPESAFE_DEFAULT_MODEL`, and `TYPESAFE_LOG_LEVEL`, or pass the same names into `typesafe.new({ ... })`. Code wins over the environment.

Default log level is `warn`. `info` prints each request URL. `debug` also prints headers (the key is redacted) and bodies. Timeout is 10 seconds per try.

## Examples

```sh
luajit examples/ticket.lua
luajit examples/choose.lua
luajit examples/noul.lua
luajit examples/score.lua
luajit examples/fanout.lua
luajit examples/thread.lua
luajit examples/models.lua
```

## Tests

```sh
eval "$(luarocks --lua-version 5.1 --local path)"
busted
```

[TypeSafe docs](https://docs.typesafe.ai/)
