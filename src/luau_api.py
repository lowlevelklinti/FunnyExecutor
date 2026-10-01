"""Luau keyword/global/UNC API tables used for monaco completions.

Kept as plain data so the webview frontend can pull it over the bridge and
register its own completion/hover/signature providers.
"""

luauKeywords = [
    "and", "break", "continue", "do", "else", "elseif", "end", "export",
    "false", "for", "function", "if", "in", "local", "nil", "not", "or",
    "repeat", "return", "then", "true", "type", "typeof", "until", "while",
]

robloxGlobals = [
    "game", "workspace", "script", "plugin", "Instance", "Enum", "Vector2",
    "Vector3", "CFrame", "UDim", "UDim2", "Color3", "BrickColor", "Ray",
    "Rect", "Region3", "Region3int16", "NumberSequence",
    "NumberSequenceKeypoint", "NumberRange", "ColorSequence",
    "ColorSequenceKeypoint", "PhysicalProperties", "TweenInfo", "DateTime",
    "Random", "Vector3int16", "Font", "Axes", "Faces", "print", "warn",
    "error", "math", "string", "table", "os", "coroutine", "task", "debug",
    "utf8", "bit32", "buffer", "tonumber", "tostring",
    "pcall", "xpcall", "select", "assert", "require", "pairs", "ipairs",
    "next", "unpack", "rawget", "rawset", "rawequal", "rawlen",
    "setmetatable", "getmetatable", "collectgarbage", "tick", "wait",
    "spawn", "delay", "elapsedTime", "_G", "shared", "self",
]

uncApi = {
    "getgenv": ("()", "Returns the global environment shared by every script."),
    "getrenv": ("()", "Returns the Roblox (sanitised) global environment."),
    "getreg": ("()", "Returns the Lua registry table."),
    "getgc": ("(includeTables)", "Returns a list of all garbage-collected values."),
    "filtergc": ("(type, options)", "Returns garbage filtered by a predicate."),
    "getsenv": ("(script)", "Returns the environment of the given script."),
    "getinstances": ("()", "Returns every Instance currently in the game."),
    "getnilinstances": ("()", "Returns instances parented to nil."),
    "getloadedmodules": ("()", "Returns all loaded ModuleScripts."),
    "getscripts": ("()", "Returns all script objects in the game."),
    "getscriptbytecode": ("(script)", "Returns the compiled bytecode of a script."),
    "getscripthash": ("(script)", "Returns the hash of a script's bytecode."),
    "getupvalue": ("(func, index)", "Returns the value of an upvalue."),
    "getupvalues": ("(func)", "Returns all upvalues of a function."),
    "setupvalue": ("(func, index, value)", "Sets the value of an upvalue."),
    "getconstant": ("(func, index)", "Returns the value of a constant."),
    "getconstants": ("(func)", "Returns all constants of a function."),
    "setconstant": ("(func, index, value)", "Overwrites a constant."),
    "getproto": ("(func, index)", "Returns a nested prototype."),
    "getprotos": ("(func)", "Returns all nested prototypes."),
    "getstack": ("(level)", "Returns the stack of a running thread."),
    "setstack": ("(level, index, value)", "Sets a stack entry."),
    "isreadonly": ("(table)", "Returns true when the table is read-only."),
    "islclosure": ("(func)", "Returns true for Lua closures."),
    "iscclosure": ("(func)", "Returns true for C closures."),
    "newcclosure": ("(func)", "Wraps a function so it reports as a C closure."),
    "loadstring": ("(code)", "Compiles a string and returns a function."),
    "gethui": ("()", "Returns a hidden UI container that is not replicated."),
    "identifyexecutor": ("()", "Returns the executor name and version."),
    "getexecutorname": ("()", "Returns the name of the current executor."),
    "getexecutorversion": ("()", "Returns the version of the current executor."),
    "setfpscap": ("(fps)", "Raises or removes the frame rate cap."),
    "getfpscap": ("()", "Returns the current frame rate cap."),
    "base64encode": ("(data)", "Encodes a string to base64."),
    "base64decode": ("(data)", "Decodes a base64 string."),
    "crypt": ("(data, key)", "Encrypts or decrypts a string."),
    "hash": ("(data)", "Hashes a string."),
    "lz4compress": ("(data)", "Compresses a string with lz4."),
    "lz4decompress": ("(data)", "Decompresses an lz4 string."),
    "dumpstring": ("(func)", "Dumps a string from a function's constants."),
    "decompile": ("(script)", "Attempts to decompile a script back to source."),
    "saveinstance": ("(options)", "Saves the current game to disk."),
    "savegame": ("()", "Saves the current place."),
    "writefile": ("(path, data)", "Writes data to a file in the workspace folder."),
    "appendfile": ("(path, data)", "Appends data to a file."),
    "readfile": ("(path)", "Reads a file and returns its contents."),
    "isfile": ("(path)", "Returns true when the path is a file."),
    "isfolder": ("(path)", "Returns true when the path is a folder."),
    "delfile": ("(path)", "Deletes a file."),
    "delfolder": ("(path)", "Deletes a folder."),
    "makefolder": ("(path)", "Creates a folder."),
    "listfiles": ("(path)", "Lists the contents of a folder."),
    "loadfile": ("(path)", "Loads a file from disk and returns a function."),
    "setclipboard": ("(text)", "Sets the system clipboard."),
    "getclipboard": ("()", "Returns the current clipboard contents."),
    "messagebox": ("(text, caption, type)", "Shows a native message box."),
    "request": ("(options)", "Performs an HTTP request."),
    "http_request": ("(options)", "Alias of request()."),
    "queue_on_teleport": ("(code)", "Runs code after a teleport."),
    "getnamecallmethod": ("()", "Returns the method name of the current namecall."),
    "setnamecallmethod": ("(name)", "Spoofs the namecall method name."),
    "getrawmetatable": ("(object)", "Returns the real metatable of an object."),
    "setrawmetatable": ("(object, metatable)", "Sets the real metatable."),
    "getcustomasset": ("(path)", "Returns a content string for ImageLabel/Sound."),
    "mouse1click": ("()", "Clicks the left mouse button."),
    "mouse2click": ("()", "Clicks the right mouse button."),
    "mouse1press": ("()", "Presses the left mouse button."),
    "mouse1release": ("()", "Releases the left mouse button."),
    "mouse2press": ("()", "Presses the right mouse button."),
    "mouse2release": ("()", "Releases the right mouse button."),
    "mousemoveabs": ("(x, y)", "Moves the cursor to absolute screen coordinates."),
    "mousemoverel": ("(x, y)", "Moves the cursor by a relative amount."),
    "getmousepos": ("()", "Returns the cursor position."),
    "keyclick": ("(key)", "Presses and releases a key."),
    "keypress": ("(key)", "Presses a key."),
    "keyrelease": ("(key)", "Releases a key."),
    "isrbxactive": ("()", "Returns true when the Roblox window is focused."),
    "iswindowactive": ("()", "Returns true when the Roblox window is focused."),
    "Drawing": ("()", "Creates a new Drawing object."),
    "WebSocket": ("(url)", "Opens a websocket connection."),
    "firesignal": ("(signal, args)", "Fires a RobloxScriptSignal."),
    "getconnections": ("(signal)", "Returns the connections of a signal."),
    "fireproximityprompt": ("(prompt)", "Triggers a ProximityPrompt."),
    "openfiledialog": ("(options)", "Opens a native file picker dialog."),
    "savefiledialog": ("(options)", "Opens a native save dialog."),
    "getrenderproperty": ("(instance, property)", "Reads a render property."),
    "setrenderproperty": ("(instance, property, value)", "Writes a render property."),
}


def buildSnippet(name, params):
    inner = params.strip()[1:-1].strip() if params.startswith("(") else ""
    if not inner:
        return name + "()"
    parts = [p.strip() for p in inner.split(",") if p.strip()]
    args = ", ".join("${%d:%s}" % (i + 1, p) for i, p in enumerate(parts))
    return "%s(%s)" % (name, args)


def comp():
    """Everything monaco needs for lua completions, hovers and signatures."""
    items = []
    for word in luauKeywords:
        items.append({"label": word, "kind": "Keyword", "detail": "keyword"})
    for word in robloxGlobals:
        items.append({"label": word, "kind": "Variable", "detail": "Roblox global"})
    for name, (params, doc) in sorted(uncApi.items()):
        items.append({
            "label": name,
            "kind": "Function",
            "detail": name + params,
            "doc": doc,
            "insert": buildSnippet(name, params),
            "snippet": True,
        })

    hover = {}
    signatures = {}
    for word in robloxGlobals:
        hover[word] = {"sig": word, "doc": "Roblox global"}
    for name, (params, doc) in uncApi.items():
        hover[name] = {"sig": name + params, "doc": doc}
        inner = params.strip()[1:-1].strip()
        signatures[name] = {
            "label": name + params,
            "doc": doc,
            "params": [p.strip() for p in inner.split(",") if p.strip()],
        }
    return {"items": items, "hover": hover, "signatures": signatures}