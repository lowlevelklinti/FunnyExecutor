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

function base64encode(data)
	local b = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
	return ((data:gsub('.', function(x)
		local r,b='',x:byte()
		for i=8,1,-1 do r=r..(b%2^i-b%2^(i-1)>0 and '1' or '0') end
		return r;
	end)..'0000'):gsub('%d%d%d?%d?%d?%d?', function(x)
		if (#x < 6) then return '' end
		local c=0
		for i=1,6 do c=c+(x:sub(i,i)=='1' and 2^(6-i) or 0) end
		return b:sub(c+1,c+1)
	end)..({ '', '==', '=' })[#data%3+1])
end

function base64decode(data)
    local b = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    data = string.gsub(data, '[^'..b..'=]', '')
    return (data:gsub('.', function(x)
        if (x == '=') then return '' end
        local r,f='',(b:find(x)-1)
        for i=6,1,-1 do r=r..(f%2^i-f%2^(i-1)>0 and '1' or '0') end
        return r;
    end):gsub('%d%d%d?%d?%d?%d?%d?%d?', function(x)
        if (#x ~= 8) then return '' end
        local c=0
        for i=1,8 do c=c+(x:sub(i,i)=='1' and 2^(8-i) or 0) end
        return string.char(c)
    end))
end

crypt = {}
crypt.base64encode = base64encode
crypt.base64decode = base64decode

-- lz4compress/lz4decompress

lz4compress = lz4.compress
lz4decompress = lz4.decompress

-- loadstring

loadstring = function(source)
	local response = send_method('compile', base64encode(source))
	return load_bytecode(base64decode(response), getfenv())
end

-- file api

writefile = function(path, content)
	local response = send_method('writefile', path, content)
	if response ~= 'ok' then
		warn('FunnyExecutor -- file error: '..tostring(response))
	end
end

appendfile = function(path, content)
	local response = send_method('appendfile', path, content)
	if response ~= 'ok' then
		warn('FunnyExecutor -- file error: '..tostring(response))
	end
end

readfile = function(path)
	local response = send_method('readfile', path)
	if response == 'fail' then
		warn('FunnyExecutor -- file error: '..tostring(response))
		return nil
	else
		return response
	end
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
	return response:split('\n')
end

-- clipboard

setclipboard = function(content)
	local response = send_method('setclipboard', content)
	if response ~= 'ok' then
		warn('FunnyExecutor -- clipboard error: '..tostring(response))
	end
end

getclipboard = function()
	local response = send_method('getclipboard')
	return response
end

toclipboard = setclipboard

-- identifyexecutor

identifyexecutor = function()
	return 'FunnyExecutor', 'v0.100'
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

-- main loop

game.StarterGui:SetCore("SendNotification", {
	Title = "FAPI",
	Text = "Attached",
	Duration = 5,
})

task.spawn(function()
	while task.wait() do
		if upd.Value ~= lastValue then
			lastValue = upd.Value
			task.spawn(function()
				local data = requestData()
				if data then
					load_bytecode(base64decode(data), getfenv())()
				end
			end)
		end
	end
end)