--[[

UNC functions:

getgenv
game:HttpGet
base64encode, base64decode (also in crypt)
lz4compress, lz4decompress
loadstring
file apis
clipboard getter/setter
identifyexecutor
request

isnetworkowner

using fiu by rce-incorporated
luau version 0.654

]]

-- create root

local folder = Instance.new("Folder")
folder.Name = "_funnyexecutor"

local upd = Instance.new("BoolValue")
upd.Name = "UpdateIndicator"
upd.Parent = folder

folder.Parent = game.CoreGui

-- vars
local http = game.HttpService
local lastValue = upd.Value
local bridgeServer = 'http://localhost:9475'

-- modules

local lz4 do
	local module = {}

	type Streamer = {
		Offset: number,
		Source: string,
		Length: number,
		IsFinished: boolean,
		LastUnreadBytes: number,

		read: (Streamer, len: number?, shiftOffset: boolean?) -> string,
		seek: (Streamer, len: number) -> (),
		append: (Streamer, newData: string) -> (),
		toEnd: (Streamer) -> ()
	}

	type BlockData = {
		[number]: {
			Literal: string,
			LiteralLength: number,
			MatchOffset: number?,
			MatchLength: number?
		}
	}

	local function plainFind(str, pat)
		return string.find(str, pat, 0, true)
	end

	local function streamer(str): Streamer
		local Stream = {}
		Stream.Offset = 0
		Stream.Source = str
		Stream.Length = string.len(str)
		Stream.IsFinished = false
		Stream.LastUnreadBytes = 0

		function Stream.read(self: Streamer, len: number?, shift: boolean?): string
			local len = len or 1
			local shift = if shift ~= nil then shift else true
			local dat = string.sub(self.Source, self.Offset + 1, self.Offset + len)

			local dataLength = string.len(dat)
			local unreadBytes = len - dataLength

			if shift then
				self:seek(len)
			end

			self.LastUnreadBytes = unreadBytes
			return dat
		end

		function Stream.seek(self: Streamer, len: number)
			local len = len or 1

			self.Offset = math.clamp(self.Offset + len, 0, self.Length)
			self.IsFinished = self.Offset >= self.Length
		end

		function Stream.append(self: Streamer, newData: string)
			-- adds new data to the end of a stream
			self.Source ..= newData
			self.Length = string.len(self.Source)
			self:seek(0) --hacky but forces a recalculation of the isFinished flag
		end

		function Stream.toEnd(self: Streamer)
			self:seek(self.Length)
		end

		return Stream
	end

	function module.compress(str: string): string
		local blocks: BlockData = {}
		local iostream = streamer(str)

		if iostream.Length > 12 then
			local firstFour = iostream:read(4)

			local processed = firstFour
			local lit = firstFour
			local match = ""
			local LiteralPushValue = ""
			local pushToLiteral = true

			repeat
				pushToLiteral = true
				local nextByte = iostream:read()

				if plainFind(processed, nextByte) then
					local next3 = iostream:read(3, false)

					if string.len(next3) < 3 then
						--push bytes to literal block then break
						LiteralPushValue = nextByte .. next3
						iostream:seek(3)
					else
						match = nextByte .. next3

						local matchPos = plainFind(processed, match)
						if matchPos then
							iostream:seek(3)
							repeat
								local nextMatchByte = iostream:read(1, false)
								local newResult = match .. nextMatchByte

								local repos = plainFind(processed, newResult)
								if repos then
									match = newResult
									matchPos = repos
									iostream:seek(1)
								end
							until not plainFind(processed, newResult) or iostream.IsFinished

							local matchLen = string.len(match)
							local pushMatch = true

							if iostream.Length - iostream.Offset <= 5 then
								LiteralPushValue = match
								pushMatch = false
								--better safe here, dont bother pushing to match ever
							end

							if pushMatch then
								pushToLiteral = false

								-- gets the position from the end of processed, then slaps it onto processed
								local realPosition = string.len(processed) - matchPos
								processed = processed .. match

								table.insert(blocks, {
									Literal = lit,
									LiteralLength = string.len(lit),
									MatchOffset = realPosition + 1,
									MatchLength = matchLen,
								})
								lit = ""
							end
						else
							LiteralPushValue = nextByte
						end
					end
				else
					LiteralPushValue = nextByte
				end

				if pushToLiteral then
					lit = lit .. LiteralPushValue
					processed = processed .. nextByte
				end
			until iostream.IsFinished
			table.insert(blocks, {
				Literal = lit,
				LiteralLength = string.len(lit)
			})
		else
			local str = iostream.Source
			blocks[1] = {
				Literal = str,
				LiteralLength = string.len(str)
			}
		end

		-- generate the output chunk
		-- %s is for adding header
		local output = string.rep("\x00", 4)
		local function write(char)
			output = output .. char
		end
		-- begin working through chunks
		for chunkNum, chunk in blocks do
			local litLen = chunk.LiteralLength
			local matLen = (chunk.MatchLength or 4) - 4

			-- create token
			local tokenLit = math.clamp(litLen, 0, 15)
			local tokenMat = math.clamp(matLen, 0, 15)

			local token = bit32.lshift(tokenLit, 4) + tokenMat
			write(string.pack("<I1", token))

			if litLen >= 15 then
				litLen = litLen - 15
				--begin packing extra bytes
				repeat
					local nextToken = math.clamp(litLen, 0, 0xFF)
					write(string.pack("<I1", nextToken))
					if nextToken == 0xFF then
						litLen = litLen - 255
					end
				until nextToken < 0xFF
			end

			-- push raw lit data
			write(chunk.Literal)

			if chunkNum ~= #blocks then
				-- push offset as u16
				write(string.pack("<I2", chunk.MatchOffset))

				-- pack extra match bytes
				if matLen >= 15 then
					matLen = matLen - 15

					repeat
						local nextToken = math.clamp(matLen, 0, 0xFF)
						write(string.pack("<I1", nextToken))
						if nextToken == 0xFF then
							matLen = matLen - 255
						end
					until nextToken < 0xFF
				end
			end
		end
		--append chunks
		local compLen = string.len(output) - 4
		local decompLen = iostream.Length

		return string.pack("<I4", compLen) .. string.pack("<I4", decompLen) .. output
	end

	function module.decompress(lz4data: string): string
		local inputStream = streamer(lz4data)

		local compressedLen = string.unpack("<I4", inputStream:read(4))
		local decompressedLen = string.unpack("<I4", inputStream:read(4))
		local reserved = string.unpack("<I4", inputStream:read(4))

		if compressedLen == 0 then
			return inputStream:read(decompressedLen)
		end

		local outputStream = streamer("")

		repeat
			local token = string.byte(inputStream:read())
			local litLen = bit32.rshift(token, 4)
			local matLen = bit32.band(token, 15) + 4

			if litLen >= 15 then
				repeat
					local nextByte = string.byte(inputStream:read())
					litLen += nextByte
				until nextByte ~= 0xFF
			end

			local literal = inputStream:read(litLen)
			outputStream:append(literal)
			outputStream:toEnd()
			if outputStream.Length < decompressedLen then
				--match
				local offset = string.unpack("<I2", inputStream:read(2))
				if matLen >= 19 then
					repeat
						local nextByte = string.byte(inputStream:read())
						matLen += nextByte
					until nextByte ~= 0xFF
				end

				outputStream:seek(-offset)
				local pos = outputStream.Offset
				local match = outputStream:read(matLen)
				local unreadBytes = outputStream.LastUnreadBytes
				local extra
				if unreadBytes then
					repeat
						outputStream.Offset = pos
						extra = outputStream:read(unreadBytes)
						unreadBytes = outputStream.LastUnreadBytes
						match ..= extra
					until unreadBytes <= 0
				end

				outputStream:append(match)
				outputStream:toEnd()
			end

		until outputStream.Length >= decompressedLen

		return outputStream.Source
	end

	lz4 = module
end

-- funcs

local function requestData()
	local result, success = nil

	local exists, _ = pcall(function()
		http:RequestInternal({
			Url = bridgeServer,
			Method = "GET",
			Headers = {
				['Content-Type'] = "text/plain"
			}
		}):Start(function(s,b)
			result = b
			result['Success'] = s
		end)
	end)

	if not exists then
		result = {
			Success = true,
			Body = workspace.Fallback.Value
		}
	end

	repeat task.wait() until result

	if not result or not result.Success then
		warn('FunnyExecutor -- request error')
		return nil
	end

	return result and result.Body or ""
end

local function send_method(method, ...)
	local result, success = nil

	local body = table.concat({method, ...}, '\n')

	local exists, _ = pcall(function()
		http:RequestInternal({
			Url = bridgeServer,
			Method = "POST",
			Body = body,
			Headers = {
				['Content-Type'] = "text/plain"
			}
		}):Start(function(s,b)
			result = b
			result['Success'] = s
		end)
	end)

	if not exists then
		result = {
			Success = true,
			Body = workspace.Fallback.Value
		}
	end

	repeat task.wait() until result

	if not result or not result.Success then
		warn('FunnyExecutor -- request error')
		return nil
	end

	return result and result.Body or ""
end

-- unc functions

getgenv = function()
	return getfenv()
end

-- game:HttpGet()

local game_o = game
game = {
	HttpGet = function(self, url)
		local result = nil

		http:RequestInternal({
			Url = url,
			Method = "GET",
			Headers = {
				['Content-Type'] = "text/plain"
			}
		}):Start(function(s,b)
			result = b
			result['Success'] = s
		end)

		repeat task.wait() until result

		if not result or not result.Success then
			warn('FunnyExecutor -- request error')
			return nil
		end

		return result and result.Body or ""
	end
}
game.HttpGetAsync = game.HttpGet

setmetatable(game, {
	__index = function(_, key)
		local value = game_o[key]

		if type(value) == "function" then
			return function(_, ...)
				return value(game_o, ...)
			end
		end

		return value
	end,

	__tostring = function()
		return tostring(game_o)
	end
})

table.freeze(game)

-- base64encode/base64decode

local b64_alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
local b64_bytes = {string.byte(b64_alphabet, 1, #b64_alphabet)}

function base64encode(data)
	local out = table.create(math.ceil(#data / 3) * 4)
	local n = 0

	for i = 1, #data - 2, 3 do
		local chunk = string.byte(data, i) * 65536 + string.byte(data, i + 1) * 256 + string.byte(data, i + 2)
		n += 1
		out[n] = string.char(
			b64_bytes[bit32.rshift(chunk, 18) + 1],
			b64_bytes[bit32.band(bit32.rshift(chunk, 12), 63) + 1],
			b64_bytes[bit32.band(bit32.rshift(chunk, 6), 63) + 1],
			b64_bytes[bit32.band(chunk, 63) + 1]
		)
	end

	local rest = #data % 3
	if rest == 1 then
		local chunk = string.byte(data, #data)
		n += 1
		out[n] = string.char(
			b64_bytes[bit32.rshift(chunk, 2) + 1],
			b64_bytes[bit32.band(bit32.lshift(chunk, 4), 63) + 1],
			61, 61
		)
	elseif rest == 2 then
		local chunk = string.byte(data, #data - 1) * 256 + string.byte(data, #data)
		n += 1
		out[n] = string.char(
			b64_bytes[bit32.rshift(chunk, 10) + 1],
			b64_bytes[bit32.band(bit32.rshift(chunk, 4), 63) + 1],
			b64_bytes[bit32.band(bit32.lshift(chunk, 2), 63) + 1],
			61
		)
	end

	return table.concat(out)
end

function base64decode(data)
	local lookup = {}
	data = string.gsub(data, '[^' .. b64_alphabet .. '=]', '')

	for i = 1, #b64_alphabet do
		lookup[string.byte(b64_alphabet, i)] = i - 1
	end

	local padding = 0
	while string.byte(data, #data - padding) == 61 do
		padding += 1
	end

	local stripped = #data - padding
	local out = table.create(stripped // 4 * 3 + 3)
	local n = 0

	for i = 1, stripped - 3, 4 do
		local chunk = lookup[string.byte(data, i)] * 262144
			+ lookup[string.byte(data, i + 1)] * 4096
			+ lookup[string.byte(data, i + 2)] * 64
			+ lookup[string.byte(data, i + 3)]
		n += 1
		out[n] = string.char(
			bit32.band(bit32.rshift(chunk, 16), 255),
			bit32.band(bit32.rshift(chunk, 8), 255),
			bit32.band(chunk, 255)
		)
	end

	local rest = stripped % 4
	if rest == 2 then
		local i = stripped - 1
		local c1 = lookup[string.byte(data, i)]
		local c2 = lookup[string.byte(data, i + 1)]
		n += 1
		out[n] = string.char(bit32.band(bit32.lshift(c1, 2) + bit32.rshift(c2, 4), 255))
	elseif rest == 3 then
		local i = stripped - 2
		local c1 = lookup[string.byte(data, i)]
		local c2 = lookup[string.byte(data, i + 1)]
		local c3 = lookup[string.byte(data, i + 2)]
		n += 1
		out[n] = string.char(
			bit32.band(bit32.lshift(c1, 2) + bit32.rshift(c2, 4), 255),
			bit32.bor(bit32.band(bit32.lshift(c2, 4), 255), bit32.rshift(c3, 2))
		)
	end

	return table.concat(out)
end

crypt = {}
crypt.base64encode = base64encode
crypt.base64decode = base64decode

crypt.generatekey = function(len)
	local alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
	local key = ''
	for i = 1, len or 32 do
		local n = math.random(1, #alphabet)
		key ..= alphabet:sub(n, n)
	end
	return key
end

crypt.generatebytes = crypt.generatekey
crypt.random = crypt.generatekey

crypt.encrypt = function(data, key)
	data = tostring(data)
	key = tostring(key)
	local result = table.create(#data)
	for i = 1, #data do
		result[i] = string.char(bit32.bxor(string.byte(data, i), string.byte(key, (i - 1) % #key + 1)))
	end
	return table.concat(result), key
end

crypt.decrypt = crypt.encrypt

crypt.hash = function(data, hash_name)
	assert(type(data) == 'string', "invalid argument #1 to 'crypt.hash' (string expected, got " .. type(data) .. ')', 2)
	assert(type(hash_name) == 'string', "invalid argument #2 to 'crypt.hash' (string expected, got " .. type(hash_name) .. ')', 2)

	local response = send_method('hash', hash_name, base64encode(data))
	if response == 'fail' then
		return nil
	end
	return response
end

-- lz4compress/lz4decompress

lz4compress = lz4.compress
lz4decompress = lz4.decompress

-- loadstring

loadstring = function(source)
	local response = send_method('compile', base64encode(source))
	if not response or response:sub(1, 4) == 'fail' then
		return nil, 'FunnyExecutor -- loadstring error: ' .. tostring(response)
	end
	return load_bytecode(base64decode(response), getfenv())
end

-- file api

local blocked_extensions = {".exe", ".scr", ".bat", ".com", ".csh", ".msi", ".vb", ".vbs",
	".vbe", ".ws", ".wsf", ".wsh", ".ps1", ".py", ".apk", ".pif", ".cpl", ".msc",
	".jar", ".cmd", ".hta", ".gadget", ".inf", ".ins", ".isp", ".psd1", ".psm1",
	".reg", ".scf", ".shb", ".sys", ".js", ".jse", ".lnk", ".msp",
	".zip", ".rar", ".7z", ".tar", ".gz", ".cab", ".iso", ".img",
	".dll", ".ocx", ".drv", ".vxd", ".xml", ".ini", ".cpp", ".c", ".url", ".uri",
	".deb", ".rpm", ".sh", ".bash", ".zsh", ".fish", ".npm"}

local function isBlockedExtension(path: string): boolean
	-- windows strips trailing dots/spaces, so "file.exe " counts as ".exe"
	local name = (path:lower():gsub("[%s.]+$", ""))
	for _, ext in blocked_extensions do
		if name:sub(-#ext) == ext then
			return true
		end
	end
	return false
end

writefile = function(path, content)
	if isBlockedExtension(path) then
		warn('FunnyExecutor -- writefile blocked: ' .. path)
		return
	end
	-- content is base64'd in transit so newlines and binary bytes survive the bridge protocol
	local response = send_method('writefile', path, base64encode(content))
	if response ~= 'ok' then
		warn('FunnyExecutor -- file error: '..tostring(response))
	end
end

appendfile = function(path, content)
	if isBlockedExtension(path) then
		warn('FunnyExecutor -- appendfile blocked: ' .. path)
		return
	end
	local response = send_method('appendfile', path, base64encode(content))
	if response ~= 'ok' then
		warn('FunnyExecutor -- file error: '..tostring(response))
	end
end

readfile = function(path)
	local response = send_method('readfile', path)
	if response == 'fail' then
		warn('FunnyExecutor -- file error: '..tostring(response))
		return nil
	end
	return base64decode(response)
end

isfile = function(path)
	local response = send_method('isfile', path)
	if response ~= 'true' and response ~= 'false' then
		warn('FunnyExecutor -- file error: '..tostring(response))
	end
	return response == 'true'
end

isfolder = function(path)
	local response = send_method('isfolder', path)
	if response ~= 'true' and response ~= 'false' then
		warn('FunnyExecutor -- file error: '..tostring(response))
		return nil
	end
	return response == 'true'
end

delfile = function(path)
	local response = send_method('delfile', path)
	if response ~= 'ok' then
		warn('FunnyExecutor -- file error: '..tostring(response))
	end
end

delfolder = function(path)
	local response = send_method('delfolder', path)
	if response ~= 'ok' then
		warn('FunnyExecutor -- file error: '..tostring(response))
	end
end

makefolder = function(path)
	local response = send_method('makefolder', path)
	if response ~= 'ok' then
		warn('FunnyExecutor -- file error: '..tostring(response))
	end
end

listfiles = function(path)
	local response = send_method('listfiles', path)
	if response == 'fail' then
		warn('FunnyExecutor -- listfiles: folder not found: ' .. tostring(path))
		return {}
	end
	if response == '' then
		return {}
	end
	return response:split('\n')
end

-- loadfile

loadfile = function(path: string)
	local content = readfile(path)
	if not content then
		return nil, 'FunnyExecutor -- loadfile: unable to read \'' .. tostring(path) .. '\''
	end

	local ok, result = pcall(loadstring, content)
	if not ok or result == nil then
		return nil, 'FunnyExecutor -- loadfile: ' .. tostring(result)
	end

	return result
end

-- setfpscap

setfpscap = function(fps: number)
	if type(fps) ~= 'number' then
		error('setfpscap expects a number', 2)
	end

	local response = send_method('setfpscap', tostring(math.floor(fps + 0.5)))
	if response ~= 'ok' then
		warn('FunnyExecutor -- setfpscap failed: ' .. tostring(fps))
	end
end

getfpscap = function()
	local response = send_method('getfpscap')
	local cap = tonumber(response)
	if not cap then
		warn('FunnyExecutor -- getfpscap failed')
		return nil
	end
	return cap
end

local function pointer_request(method_name, script)
	local holder = Instance.new('ObjectValue')
	holder.Name = http:GenerateGUID(false)
	holder.Value = script
	holder.Parent = folder

	local response = send_method(method_name, holder.Name)
	holder:Destroy()

	return response
end

getscriptbytecode = function(script)
	assert(typeof(script) == 'Instance' and script:IsA('LuaSourceContainer'), "invalid argument #1 to 'getscriptbytecode' (LuaSourceContainer expected, got " .. typeof(script) .. ')', 2)

	local response = pointer_request('getscriptbytecode', script)
	if not response or response == 'fail' then
		return nil
	end
	return base64decode(response)
end

dumpstring = getscriptbytecode

getscripthash = function(script)
	assert(typeof(script) == 'Instance' and script:IsA('LuaSourceContainer'), "invalid argument #1 to 'getscripthash' (LuaSourceContainer expected, got " .. typeof(script) .. ')', 2)

	local response = pointer_request('getscripthash', script)
	if not response or response == 'fail' then
		return nil
	end
	return response
end

-- clipboard

setclipboard = function(content)
	local response = send_method('setclipboard', base64encode(tostring(content)))
	if response ~= 'ok' then
		warn('FunnyExecutor -- clipboard error: '..tostring(response))
	end
end

getclipboard = function()
	local response = send_method('getclipboard')
	return response
end

toclipboard = setclipboard

local input_methods = {
	mouse1click = 'mouse1click',
	mouse2click = 'mouse2click',
	middleclick = 'middleclick',
	mouse1press = 'mouse1down',
	mouse1release = 'mouse1up',
	mouse2press = 'mouse2down',
	mouse2release = 'mouse2up',
	middlepress = 'middledown',
	middlerelease = 'middleup',
	movemouse = 'movemouse',
	mousemoveabs = 'mousemoveabs',
	mouserel = 'movemouserel',
	mousemoverel = 'movemouserel',
	keyclick = 'keyclick',
	keypress = 'keypress',
	keyrelease = 'keyrelease',
}

for name, method in input_methods do
	_G[name] = function(...)
		local response = send_method(method, ...)
		if response == 'fail' then
			warn('FunnyExecutor -- input error: ' .. name)
		end
	end
end

getmousepos = function()
	local response = send_method('getmousepos')
	local x, y = response:match('^(%-?%d+),(%-?%d+)$')
	if not x then
		return nil, nil
	end
	return tonumber(x), tonumber(y)
end

getmouselocation = getmousepos

iswindowactive = function()
	return send_method('iswindowactive') == 'true'
end

isrbxactive = iswindowactive

messagebox = function(text, title, flags)
	local response = send_method('messagebox', base64encode(tostring(text)), base64encode(tostring(title or 'FunnyExecutor')), tostring(flags or 0))
	return tonumber(response)
end

-- identifyexecutor

identifyexecutor = function()
	return 'FunnyExecutor', 'v0.220'
end

getexecutorname = function()
	return identifyexecutor()
end

getexecutorversion = function()
	return select(2, identifyexecutor())
end

-- executor env extensions

local executor_closures = {}
setmetatable(executor_closures, {__mode = 'k'})

islclosure = function(func)
	assert(type(func) == 'function', "invalid argument #1 to 'islclosure' (function expected, got " .. type(func) .. ')', 2)
	return debug.info(func, 's') ~= '[C]'
end

isluaclosure = islclosure

iscclosure = function(func)
	assert(type(func) == 'function', "invalid argument #1 to 'iscclosure' (function expected, got " .. type(func) .. ')', 2)
	return debug.info(func, 's') == '[C]'
end

newcclosure = function(func)
	assert(type(func) == 'function', "invalid argument #1 to 'newcclosure' (function expected, got " .. type(func) .. ')', 2)
	local wrapped = coroutine.wrap(function(...)
		while true do
			coroutine.yield(func(...))
		end
	end)
	executor_closures[wrapped] = true
	return wrapped
end

clonefunction = function(func)
	assert(type(func) == 'function', "invalid argument #1 to 'clonefunction' (function expected, got " .. type(func) .. ')', 2)
	if iscclosure(func) then
		return newcclosure(func)
	end
	return function(...)
		return func(...)
	end
end

isexecutorclosure = function(func)
	if type(func) ~= 'function' then
		error("invalid argument #1 to 'isexecutorclosure' (function expected, got " .. type(func) .. ')', 2)
	end

	if executor_closures[func] then
		return true
	end

	if iscclosure(func) then
		return debug.info(func, 'n') == ''
	end

	local ok, fenv = pcall(getfenv, func)
	if not ok then
		return false
	end

	if typeof(fenv.script) ~= 'Instance' then
		return true
	end

	if fenv.script.Name == 'AvatarEditorPrompts' or fenv.script.Name == 'JestGlobals' then
		return false
	end

	if fenv.script.Parent == nil then
		return true
	end

	if fenv == getfenv(0) then
		return true
	end

	return true
end

checkclosure = isexecutorclosure
isourclosure = isexecutorclosure

-- cloneref / compareinstances

local clonerefs = {}
setmetatable(clonerefs, {__mode = 'k'})

cloneref = function(obj)
	local proxy = newproxy(true)
	local meta = getmetatable(proxy)
	meta.__index = function(t, n)
		local v = obj[n]
		if typeof(v) == 'function' then
			return function(self, ...)
				if self == t then
					self = obj
				end
				return v(self, ...)
			end
		end
		return v
	end
	meta.__newindex = function(_, n, v)
		obj[n] = v
	end
	meta.__tostring = function()
		return tostring(obj)
	end
	meta.__metatable = getmetatable(obj)
	clonerefs[proxy] = obj
	return proxy
end

compareinstances = function(a, b)
	assert(type(a) == 'userdata', "invalid argument #1 to 'compareinstances' (Instance expected, got " .. typeof(a) .. ')', 2)
	assert(type(b) == 'userdata', "invalid argument #2 to 'compareinstances' (Instance expected, got " .. typeof(b) .. ')', 2)
	if clonerefs[a] then
		a = clonerefs[a]
	end
	if clonerefs[b] then
		b = clonerefs[b]
	end
	return a == b
end

-- report cloneref proxies as Instances (what sunc checks for)

local rtypeof = typeof
typeof = function(obj)
	if clonerefs[obj] then
		return 'Instance'
	end
	return rtypeof(obj)
end

-- getnamecallmethod (error-probe technique, ported from the reference env)

local function generate_error(object)
	local _, err = xpcall(function()
		object:__namecall()
	end, function()
		return debug.info(2, 'f')
	end)
	return err
end

local first_probe = generate_error(OverlapParams.new())
local second_probe = generate_error(Color3.new())

local cached_methods = {}
setmetatable(cached_methods, {__mode = 'k'})

getnamecallmethod = function()
	local method = nil

	local _, err = pcall(first_probe)
	if type(err) == 'string' then
		method = err:match('^(.+) is not a valid member of %w+$')
	end

	if not method then
		_, err = pcall(second_probe)
		if type(err) == 'string' then
			method = err:match('^(.+) is not a valid member of %w+$')
		end
	end

	if not method or method == '__namecall' then
		return cached_methods[coroutine.running()]
	end

	cached_methods[coroutine.running()] = method
	return method
end

-- gethui (created lazily, only when first called)

local hidden_ui = nil

gethui = function()
	if hidden_ui and hidden_ui.Parent then
		return hidden_ui
	end

	local ok, gui = pcall(function()
		local screen_gui = Instance.new('ScreenGui')
		screen_gui.Name = 'RobloxUi'
		screen_gui.ResetOnSpawn = false
		screen_gui.DisplayOrder = 999999
		screen_gui.Parent = game:GetService('CoreGui')
		return screen_gui
	end)

	if ok then
		hidden_ui = gui
	end

	return hidden_ui
end

-- instance registry
-- tracks descendants via one signal connection + a lazy one-time scan on
-- first use (deliberately NOT a proxy-per-instance system like the reference)

local instance_registry = {}
local registry_scanned = false

local function register_instance(inst)
	instance_registry[inst] = true
end

local function ensure_registry()
	if registry_scanned then
		return
	end
	registry_scanned = true

	for _, inst in game_o:GetDescendants() do
		register_instance(inst)
	end
end

game_o.DescendantAdded:Connect(register_instance)

getnilinstances = function()
	ensure_registry()
	local result = {}

	for inst in instance_registry do
		local ok, parent = pcall(function()
			return inst.Parent
		end)
		if ok and parent == nil then
			table.insert(result, inst)
		end
	end

	return result
end

getloadedmodules = function()
	ensure_registry()
	local result = {}

	for inst in instance_registry do
		local ok, is_module = pcall(function()
			return inst:IsA('ModuleScript')
		end)
		if ok and is_module then
			table.insert(result, inst)
		end
	end

	return result
end

getscripts = function()
	ensure_registry()
	local result = {}

	for inst in instance_registry do
		local ok, matches = pcall(function()
			if inst:IsA('LocalScript') or inst:IsA('ModuleScript') then
				return true
			end
			if inst:IsA('Script') then
				local context = inst.RunContext
				return context == Enum.RunContext.Client or context == Enum.RunContext.Legacy
			end
			return false
		end)
		if ok and matches then
			table.insert(result, inst)
		end
	end

	return result
end

getrunningscripts = function()
	local result = {}

	for _, inst in getscripts() do
		local ok, matches = pcall(function()
			local full_name = inst:GetFullName()
			if full_name:find('CoreGui') or full_name:find('CorePackages') then
				return false
			end
			return inst:FindFirstAncestorOfClass('Actor') == nil
		end)
		if ok and matches then
			table.insert(result, inst)
		end
	end

	return result
end

-- isreadonly

isreadonly = function(tbl)
	assert(type(tbl) == 'table', "invalid argument #1 to 'isreadonly' (table expected, got " .. type(tbl) .. ')', 2)
	return table.isfrozen(tbl)
end

-- queue_on_teleport (file-backed: queued scripts run on next inject)

local queue_file = 'queued_teleports.lua'
local queue_marker = '\n--__FUNNYQUEUE__--\n'

queue_on_teleport = function(source)
	assert(type(source) == 'string', "invalid argument #1 to 'queue_on_teleport' (string expected, got " .. type(source) .. ')', 2)

	local existing = ''
	if isfile(queue_file) then
		existing = readfile(queue_file) or ''
	end

	if existing == '' then
		writefile(queue_file, source)
	else
		writefile(queue_file, existing .. queue_marker .. source)
	end
end

local function flush_teleport_queue()
	if not isfile(queue_file) then
		return
	end

	local content = readfile(queue_file) or ''
	delfile(queue_file)

	for _, source in content:split(queue_marker) do
		if source ~= '' then
			task.spawn(function()
				local func, err = loadstring(source)
				if func then
					func()
				else
					warn('FunnyExecutor -- queued script failed: ' .. tostring(err))
				end
			end)
		end
	end
end

-- isnetworkowner (my own idea)

isnetworkowner = function(part: BasePart)
	if part.Anchored or part:IsGrounded() or not part or not part:IsA("BasePart") then
		return false
	end
	return part.ReceiveAge == 0
end

-- request

request = function(options)
	local result = nil

	http:RequestInternal({
		Url = options.Url,
		Method = options.Method or "GET",
		Headers = options.Headers or {},
		Cookies = options.Cookies or {},
		Body = options.Body
	}):Start(function(s,b)
		result = b
		result['Success'] = s
	end)

	repeat task.wait() until result

	if not result or not result.Success then
		warn('FunnyExecutor -- request error')
		return nil
	end

	return result
end

http_request = request
syn = {
	request = request
}

-- main loop

game.StarterGui:SetCore("SendNotification", {
	Title = "FAPI",
	Text = "Attached",
	Duration = 5,
})

flush_teleport_queue()

task.spawn(function()
	while task.wait() do
		if upd.Value ~= lastValue then
			lastValue = upd.Value
			task.spawn(function()
				local data = requestData()
				if data then
					local ok, err = pcall(function()
						load_bytecode(data, getfenv())()
					end)
					if not ok then
						warn('FunnyExecutor -- execution error: ' .. tostring(err))
					end
				end
			end)
		end
	end
end)