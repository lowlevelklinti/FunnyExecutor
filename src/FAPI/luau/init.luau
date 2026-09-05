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

		local output = ""
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

		return output
	end

	function module.decompress(lz4data: string, decompressedLen: number?): string
		local inputStream = streamer(lz4data)
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

			if inputStream.IsFinished then
				break
			end

			if decompressedLen and outputStream.Length >= decompressedLen then
				break
			end

			local offset = string.unpack("<I2", inputStream:read(2))
			if bit32.band(token, 15) >= 15 then
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

			if inputStream.IsFinished then
				break
			end

		until decompressedLen ~= nil and outputStream.Length >= decompressedLen

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

local genv_table = {}

getgenv = function()
	return genv_table
end

do
	local ok = pcall(function()
		local env = getfenv()
		local meta = getmetatable(env)
		if type(meta) ~= 'table' then
			meta = {}
		end
		meta.__index = genv_table
		setmetatable(env, meta)
	end)
end

local renv_table = {
	game = game,
	workspace = workspace,
	script = script,
	Instance = Instance,
	Enum = Enum,
	task = task,
	coroutine = coroutine,
	print = print,
	warn = warn,
	error = error,
	assert = assert,
	pcall = pcall,
	xpcall = xpcall,
	select = select,
	tonumber = tonumber,
	tostring = tostring,
	type = type,
	typeof = typeof,
	tick = tick,
	wait = wait,
	spawn = spawn,
	delay = delay,
	require = require,
	math = math,
	string = string,
	table = table,
	os = os,
	bit32 = bit32,
	buffer = buffer,
	utf8 = utf8,
	_G = {},
}

getrenv = function()
	return renv_table
end


local AES = {}
do
	local s_box = { 99, 124, 119, 123, 242, 107, 111, 197,  48,   1, 103,  43, 254, 215, 171, 118, 202,
		130, 201, 125, 250,  89,  71, 240, 173, 212, 162, 175, 156, 164, 114, 192, 183, 253, 147,  38,  54,
		 63, 247, 204,  52, 165, 229, 241, 113, 216,  49,  21,   4, 199,  35, 195,  24, 150,   5, 154,   7,
		 18, 128, 226, 235,  39, 178, 117,   9, 131,  44,  26,  27, 110,  90, 160,  82,  59, 214, 179,  41,
		227,  47, 132,  83, 209,   0, 237,  32, 252, 177,  91, 106, 203, 190,  57,  74,  76,  88, 207, 208,
		239, 170, 251,  67,  77,  51, 133,  69, 249,   2, 127,  80,  60, 159, 168,  81, 163,  64, 143, 146,
		157,  56, 245, 188, 182, 218,  33,  16, 255, 243, 210, 205,  12,  19, 236,  95, 151,  68,  23, 196,
		167, 126,  61, 100,  93,  25, 115,  96, 129,  79, 220,  34,  42, 144, 136,  70, 238, 184,  20, 222,
		 94,  11, 219, 224,  50,  58,  10,  73,   6,  36,  92, 194, 211, 172,  98, 145, 149, 228, 121, 231,
		200,  55, 109, 141, 213,  78, 169, 108,  86, 244, 234, 101, 122, 174,   8, 186, 120,  37,  46,  28,
		166, 180, 198, 232, 221, 116,  31,  75, 189, 139, 138, 112,  62, 181, 102,  72,   3, 246,  14,  97,
		 53,  87, 185, 134, 193,  29, 158, 225, 248, 152,  17, 105, 217, 142, 148, 155,  30, 135, 233, 206,
		 85,  40, 223, 140, 161, 137,  13, 191, 230,  66, 104,  65, 153,  45,  15, 176,  84, 187,  22}
	local inv_s_box = { 82,   9, 106, 213,  48,  54, 165,  56, 191,  64, 163, 158, 129, 243, 215, 251, 124,
		227,  57, 130, 155,  47, 255, 135,  52, 142,  67,  68, 196, 222, 233, 203,  84, 123, 148,  50, 166,
		194,  35,  61, 238,  76, 149,  11,  66, 250, 195,  78,   8,  46, 161, 102,  40, 217,  36, 178, 118,
		 91, 162,  73, 109, 139, 209,  37, 114, 248, 246, 100, 134, 104, 152,  22, 212, 164,  92, 204,  93,
		101, 182, 146, 108, 112,  72,  80, 253, 237, 185, 218,  94,  21,  70,  87, 167, 141, 157, 132, 144,
		216, 171,   0, 140, 188, 211,  10, 247, 228,  88,   5, 184, 179,  69,   6, 208,  44,  30, 143, 202,
		 63,  15,   2, 193, 175, 189,   3,   1,  19, 138, 107,  58, 145,  17,  65,  79, 103, 220, 234, 151,
		242, 207, 206, 240, 180, 230, 115, 150, 172, 116,  34, 231, 173,  53, 133, 226, 249,  55, 232,  28,
		117, 223, 110,  71, 241,  26, 113,  29,  41, 197, 137, 111, 183,  98,  14, 170,  24, 190,  27, 252,
		 86,  62,  75, 198, 210, 121,  32, 154, 219, 192, 254, 120, 205,  90, 244,  31, 221, 168,  51, 136,
		  7, 199,  49, 177,  18,  16,  89,  39, 128, 236,  95,  96,  81, 127, 169,  25, 181,  74,  13,  45,
		229, 122, 159, 147, 201, 156, 239, 160, 224,  59,  77, 174,  42, 245, 176, 200, 235, 187,  60, 131,
		 83, 153,  97,  23,  43,   4, 126, 186, 119, 214,  38, 225, 105,  20,  99,  85,  33,  12, 125}

	local rcon = {  0,   1,   2,   4,   8,  16,  32,  64, 128,  27,  54, 108, 216, 171,  77, 154,  47,  94,
		188,  99, 198, 151,  53, 106, 212, 179, 125, 250, 239, 197, 145,  57}

	local function xtime(x)
		local i = bit32.lshift(x, 1)
		return if bit32.band(x, 128) == 0 then i else bit32.bxor(i, 27) % 256
	end

	local function subBytes(s, inv)
		inv = if inv then inv_s_box else s_box
		for i = 1, 4 do
			for j = 1, 4 do
				s[i][j] = inv[s[i][j] + 1]
			end
		end
	end

	local function shiftRows(s, inv)
		s[1][3], s[2][3], s[3][3], s[4][3] = s[3][3], s[4][3], s[1][3], s[2][3]
		if inv then
			s[1][2], s[2][2], s[3][2], s[4][2] = s[4][2], s[1][2], s[2][2], s[3][2]
			s[1][4], s[2][4], s[3][4], s[4][4] = s[2][4], s[3][4], s[4][4], s[1][4]
		else
			s[1][2], s[2][2], s[3][2], s[4][2] = s[2][2], s[3][2], s[4][2], s[1][2]
			s[1][4], s[2][4], s[3][4], s[4][4] = s[4][4], s[1][4], s[2][4], s[3][4]
		end
	end

	local function addRoundKey(s, k)
		for i = 1, 4 do
			for j = 1, 4 do
				s[i][j] = bit32.bxor(s[i][j], k[i][j])
			end
		end
	end

	local function mixColumns(s, inv)
		local t, u
		if inv then
			for i = 1, 4 do
				t = xtime(xtime(bit32.bxor(s[i][1], s[i][3])))
				u = xtime(xtime(bit32.bxor(s[i][2], s[i][4])))
				s[i][1], s[i][2] = bit32.bxor(s[i][1], t), bit32.bxor(s[i][2], u)
				s[i][3], s[i][4] = bit32.bxor(s[i][3], t), bit32.bxor(s[i][4], u)
			end
		end

		local i
		for j = 1, 4 do
			i = s[j]
			t, u = bit32.bxor(i[1], i[2], i[3], i[4]), i[1]
			for k = 1, 4 do
				i[k] = bit32.bxor(i[k], t, xtime(bit32.bxor(i[k], i[k + 1] or u)))
			end
		end
	end

	local function bytesToMatrix(t, c, inv)
		if inv then
			table.move(c[1], 1, 4, 1, t)
			table.move(c[2], 1, 4, 5, t)
			table.move(c[3], 1, 4, 9, t)
			table.move(c[4], 1, 4, 13, t)
		else
			for i = 1, #c / 4 do
				table.clear(t[i])
				table.move(c, i * 4 - 3, i * 4, 1, t[i])
			end
		end

		return t
	end

	local function xorBytes(t, a, b)
		table.clear(t)

		for i = 1, math.min(#a, #b) do
			table.insert(t, bit32.bxor(a[i], b[i]))
		end
		return t
	end

	local function expandKey(key)
		local kc = bytesToMatrix(if #key == 16 then {{}, {}, {}, {}} elseif #key == 24 then {{}, {}, {}, {}
			, {}, {}} else {{}, {}, {}, {}, {}, {}, {}, {}}, key)
		local is = #key / 4
		local i, t, w = 2, {}, nil

		while #kc < (#key / 4 + 7) * 4 do
			w = table.clone(kc[#kc])
			if #kc % is == 0 then
				table.insert(w, table.remove(w, 1))
				for j = 1, 4 do
					w[j] = s_box[w[j] + 1]
				end
				w[1] = bit32.bxor(w[1], rcon[i])
				i += 1
			elseif #key == 32 and #kc % is == 4 then
				for j = 1, 4 do
					w[j] = s_box[w[j] + 1]
				end
			end

			table.clear(t)
			xorBytes(w, table.move(w, 1, 4, 1, t), kc[#kc - is + 1])
			table.insert(kc, w)
		end

		table.clear(t)
		for i = 1, #kc / 4 do
			table.insert(t, {})
			table.move(kc, i * 4 - 3, i * 4, 1, t[#t])
		end
		return t
	end

	local function encryptBlock(key, km, pt, ps, r)
		bytesToMatrix(ps, pt)
		addRoundKey(ps, km[1])

		for i = 2, #key / 4 + 6 do
			subBytes(ps)
			shiftRows(ps)
			mixColumns(ps)
			addRoundKey(ps, km[i])
		end
		subBytes(ps)
		shiftRows(ps)
		addRoundKey(ps, km[#km])

		return bytesToMatrix(r, ps, true)
	end

	local function decryptBlock(key, km, ct, cs, r)
		bytesToMatrix(cs, ct)

		addRoundKey(cs, km[#km])
		shiftRows(cs, true)
		subBytes(cs, true)
		for i = #key / 4 + 6, 2, - 1 do
			addRoundKey(cs, km[i])
			mixColumns(cs, true)
			shiftRows(cs, true)
			subBytes(cs, true)
		end

		addRoundKey(cs, km[1])
		return bytesToMatrix(r, cs, true)
	end

	local function to_bytes(a)
		if type(a) == "string" then
			local r = {}
			for i = 1, string.len(a), 7997 do
				table.move({string.byte(a, i, i + 7996)}, 1, 7997, i, r)
			end
			return r
		elseif type(a) == "table" then
			for _, i in ipairs(a) do
				assert(type(i) == "number" and math.floor(i) == i and 0 <= i and i < 256,
					"Unable to cast value to bytes")
			end
			return a
		else
			error("Unable to cast value to bytes", 0)
		end
	end

	local function to_string(t)
		local parts = {}
		for i = 1, #t, 7997 do
			parts[#parts + 1] = string.char(table.unpack(t, i, math.min(i + 7996, #t)))
		end
		return table.concat(parts)
	end

	function AES.encrypt_CBC(key, plainText, initVector)
		key = to_bytes(key)
		assert(#key == 16 or #key == 24 or #key == 32, "Key must be either 16, 24 or 32 bytes long")
		plainText = to_bytes(plainText)
		initVector = if initVector then to_bytes(initVector) else table.create(16, 0)
		assert(#initVector == 16, "Initialization vector must be 16 bytes long")

		local km = expandKey(key)
		local b, k, p, s, t = {}, {}, initVector, {{}, {}, {}, {}}, {}
		for i = 1, #plainText, 16 do
			table.move(plainText, i, i + 15, 1, k)
			table.move(encryptBlock(key, km, xorBytes(t, k, p), s, p), 1, 16, i, b)
		end

		return b
	end

	function AES.decrypt_CBC(key, cipherText, initVector)
		key = to_bytes(key)
		assert(#key == 16 or #key == 24 or #key == 32, "Key must be either 16, 24 or 32 bytes long")
		cipherText = to_bytes(cipherText)
		assert(#cipherText % 16 == 0, "Input must be a multiple of 16 bytes in length")
		initVector = if initVector then to_bytes(initVector) else table.create(16, 0)
		assert(#initVector == 16, "Initialization vector must be 16 bytes long")

		local km = expandKey(key)
		local b, k, p, s, t = {}, {}, initVector, {{}, {}, {}, {}}, {}
		for i = 1, #cipherText, 16 do
			table.move(cipherText, i, i + 15, 1, k)
			table.move(xorBytes(k, decryptBlock(key, km, k, s, t), p), 1, 16, i, b)
			table.move(cipherText, i, i + 15, 1, p)
		end

		return b
	end

	AES.to_string = to_string
	AES.to_bytes = to_bytes
end

-- base64encode/base64decode

local b64_alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
local b64_codes = {string.byte(b64_alphabet, 1, 64)}

local b64_lookup = {}
for i = 1, #b64_alphabet do
	b64_lookup[string.byte(b64_alphabet, i)] = i - 1
end

function base64encode(data)
	local len = #data
	if len == 0 then
		return ''
	end

	local src = buffer.fromstring(data)
	local out = buffer.create(math.ceil(len / 3) * 4)
	local o = 0

	local i = 1
	while i + 2 <= len do
		local n = buffer.readu8(src, i - 1) * 65536 + buffer.readu8(src, i) * 256 + buffer.readu8(src, i + 1)
		buffer.writeu8(out, o, b64_codes[bit32.rshift(n, 18) + 1])
		buffer.writeu8(out, o + 1, b64_codes[bit32.band(bit32.rshift(n, 12), 63) + 1])
		buffer.writeu8(out, o + 2, b64_codes[bit32.band(bit32.rshift(n, 6), 63) + 1])
		buffer.writeu8(out, o + 3, b64_codes[bit32.band(n, 63) + 1])
		o += 4
		i += 3
	end

	local rest = len - i + 1
	if rest == 1 then
		local n = buffer.readu8(src, i - 1)
		buffer.writeu8(out, o, b64_codes[bit32.rshift(n, 2) + 1])
		buffer.writeu8(out, o + 1, b64_codes[bit32.band(bit32.lshift(n, 4), 63) + 1])
		buffer.writeu8(out, o + 2, 61)
		buffer.writeu8(out, o + 3, 61)
	elseif rest == 2 then
		local n = buffer.readu8(src, i - 1) * 256 + buffer.readu8(src, i)
		buffer.writeu8(out, o, b64_codes[bit32.rshift(n, 10) + 1])
		buffer.writeu8(out, o + 1, b64_codes[bit32.band(bit32.rshift(n, 4), 63) + 1])
		buffer.writeu8(out, o + 2, b64_codes[bit32.band(bit32.lshift(n, 2), 63) + 1])
		buffer.writeu8(out, o + 3, 61)
	end

	return buffer.tostring(out)
end

function base64decode(data)
	local len = #data
	if len == 0 then
		return ''
	end

	local padding = 0
	while padding < 2 and string.byte(data, len - padding) == 61 do
		padding += 1
	end

	local stripped = len - padding
	local tail = stripped % 4
	local out = buffer.create(stripped // 4 * 3 + (tail == 2 and 1 or tail == 3 and 2 or 0))
	local o = 0

	local src = buffer.fromstring(data)
	local i = 0
	while i + 4 <= stripped do
		local a = b64_lookup[buffer.readu8(src, i)] or 0
		local b = b64_lookup[buffer.readu8(src, i + 1)] or 0
		local c = b64_lookup[buffer.readu8(src, i + 2)] or 0
		local d = b64_lookup[buffer.readu8(src, i + 3)] or 0
		buffer.writeu8(out, o, bit32.band(bit32.lshift(a, 2) + bit32.rshift(b, 4), 255))
		buffer.writeu8(out, o + 1, bit32.band(bit32.lshift(b, 4) + bit32.rshift(c, 2), 255))
		buffer.writeu8(out, o + 2, bit32.band(bit32.lshift(c, 6) + d, 255))
		o += 3
		i += 4
	end

	if tail == 2 then
		local a = b64_lookup[buffer.readu8(src, i)] or 0
		local b = b64_lookup[buffer.readu8(src, i + 1)] or 0
		buffer.writeu8(out, o, bit32.band(bit32.lshift(a, 2) + bit32.rshift(b, 4), 255))
	elseif tail == 3 then
		local a = b64_lookup[buffer.readu8(src, i)] or 0
		local b = b64_lookup[buffer.readu8(src, i + 1)] or 0
		local c = b64_lookup[buffer.readu8(src, i + 2)] or 0
		buffer.writeu8(out, o, bit32.band(bit32.lshift(a, 2) + bit32.rshift(b, 4), 255))
		buffer.writeu8(out, o + 1, bit32.band(bit32.lshift(b, 4) + bit32.rshift(c, 2), 255))
	end

	return buffer.tostring(out)
end

crypt = {}
crypt.base64encode = base64encode
crypt.base64decode = base64decode

crypt.base64 = {
	encode = base64encode,
	decode = base64decode,
}

base64 = {
	encode = base64encode,
	decode = base64decode,
}

base64_encode = base64encode
base64_decode = base64decode
crypt.base64_encode = base64encode
crypt.base64_decode = base64decode

crypt.generatekey = function(len)
	len = len or 32
	local bytes = table.create(len)
	for i = 1, len do
		bytes[i] = math.random(0, 255)
	end
	return base64encode(string.char(table.unpack(bytes, 1, len)))
end

crypt.generatebytes = function(size)
	assert(type(size) == 'number', "invalid argument #1 to 'crypt.generatebytes' (number expected, got " .. type(size) .. ')', 2)
	return base64encode(crypt.random(size))
end

local random_charset do
	local chars = {}
	for ascii = 33, 57 do
		chars[#chars + 1] = string.char(ascii)
	end
	for ascii = 65, 90 do
		chars[#chars + 1] = string.char(ascii)
	end
	for ascii = 97, 122 do
		chars[#chars + 1] = string.char(ascii)
	end
	random_charset = chars
end

crypt.random = function(size)
	size = tonumber(size) or error("Expected number within range (0, 1024), got: " .. tostring(size), 0)
	if size > 1024 or size < 0 then
		error("Expected number within range (0, 1024), got: " .. tostring(size), 0)
	end

	local randomString = table.create(size)
	for i = 1, size do
		randomString[i] = random_charset[math.random(1, #random_charset)]
	end

	return table.concat(randomString)
end

crypt.encrypt = function(data, key, initVector, mode)
	mode = mode or 'CBC'
	if mode ~= 'CBC' then
		error('Unsupported crypt.encrypt mode: ' .. tostring(mode), 0)
	end

	local keyBytes = AES.to_bytes(base64decode(key))
	assert(#keyBytes == 16 or #keyBytes == 24 or #keyBytes == 32, "Key must be either 16, 24 or 32 bytes long")
	local ivBytes = AES.to_bytes(base64decode(initVector))
	assert(#ivBytes == 16, "Initialization vector must be 16 bytes long")

	local plain = AES.to_bytes(tostring(data))
	local pad = 16 - (#plain % 16)
	for _ = 1, pad do
		plain[#plain + 1] = pad
	end

	local cipher = AES.encrypt_CBC(keyBytes, plain, ivBytes)
	return base64encode(AES.to_string(cipher))
end

crypt.decrypt = function(data, key, initVector, mode)
	mode = mode or 'CBC'
	if mode ~= 'CBC' then
		error('Unsupported crypt.decrypt mode: ' .. tostring(mode), 0)
	end

	local keyBytes = AES.to_bytes(base64decode(key))
	assert(#keyBytes == 16 or #keyBytes == 24 or #keyBytes == 32, "Key must be either 16, 24 or 32 bytes long")
	local ivBytes = AES.to_bytes(base64decode(initVector))
	assert(#ivBytes == 16, "Initialization vector must be 16 bytes long")

	local plain = AES.decrypt_CBC(keyBytes, AES.to_bytes(base64decode(data)), ivBytes)

	local pad = plain[#plain]
	if pad and pad >= 1 and pad <= 16 and #plain >= pad then
		local valid = true
		for i = #plain - pad + 1, #plain do
			if plain[i] ~= pad then
				valid = false
				break
			end
		end
		if valid then
			for _ = 1, pad do
				table.remove(plain)
			end
		end
	end

	return AES.to_string(plain)
end

crypt.hmac = function(key, data, algorithm)
	assert(type(key) == 'string', "invalid argument #1 to 'crypt.hmac' (string expected, got " .. type(key) .. ')', 2)
	assert(type(data) == 'string', "invalid argument #2 to 'crypt.hmac' (string expected, got " .. type(data) .. ')', 2)

	local response = send_method('hmac', algorithm or 'sha256', base64encode(key), base64encode(data))
	if response == 'fail' or response == '' then
		return nil
	end
	return response
end

crypt.hash = function(data, hash_name)
	assert(type(data) == 'string', "invalid argument #1 to 'crypt.hash' (string expected, got " .. type(data) .. ')', 2)
	assert(type(hash_name) == 'string', "invalid argument #2 to 'crypt.hash' (string expected, got " .. type(hash_name) .. ')', 2)

	local response = send_method('hash', hash_name, base64encode(data))
	if response == 'fail' then
		return nil
	end
	return response
end

lz4compress = lz4.compress
lz4decompress = lz4.decompress
crypt.lz4compress = lz4.compress
crypt.lz4decompress = lz4.decompress

local chunk_sources = setmetatable({}, {__mode = 'k'})

local real_debug = debug
local real_debug_info = real_debug.info

debug = setmetatable({}, {__index = real_debug})

debug.info = function(f, what)
	what = what or 'sl'
	local target = f
	if type(f) == 'number' then
		local okn, func = pcall(real_debug_info, f + 1, 'f')
		target = okn and func or nil
	end

	local name = type(target) == 'function' and chunk_sources[target]
	if name and type(what) == 'string' and what:find('s', 1, true) then
		if what == 's' then
			return name
		end
		local vals = {}
		for i = 1, #what do
			local opt = what:sub(i, i)
			if opt == 's' then
				vals[#vals + 1] = name
			else
				local oko, part = pcall(real_debug_info, target, opt)
				vals[#vals + 1] = oko and part or nil
			end
		end
		return table.unpack(vals, 1, #what)
	end

	return real_debug_info(f, what)
end

loadstring = function(source, chunkname)
	if chunkname then
		chunkname = tostring(chunkname):gsub('^[@=]', '')
	end

	local response = send_method('compile', base64encode(source), base64encode(chunkname or ''))
	if not response or response:sub(1, 4) == 'fail' then
		return nil, 'FunnyExecutor -- loadstring error: ' .. tostring(response)
	end
	local func = load_bytecode(base64decode(response), getfenv())
	if chunkname and chunkname ~= '' then
		chunk_sources[func] = chunkname
	end
	return func
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
	assert(type(path) == 'string', "invalid argument #1 to 'writefile' (string expected, got " .. type(path) .. ')', 2)
	if isBlockedExtension(path) then
		error('FunnyExecutor -- writefile: extension is blocked: ' .. path, 2)
	end
	local response = send_method('writefile', path, base64encode(content))
	if response ~= 'ok' then
		error('FunnyExecutor -- writefile: ' .. tostring(response) .. ': ' .. path, 2)
	end
end

appendfile = function(path, content)
	assert(type(path) == 'string', "invalid argument #1 to 'appendfile' (string expected, got " .. type(path) .. ')', 2)
	if isBlockedExtension(path) then
		error('FunnyExecutor -- appendfile: extension is blocked: ' .. path, 2)
	end
	local response = send_method('appendfile', path, base64encode(content))
	if response ~= 'ok' then
		error('FunnyExecutor -- appendfile: ' .. tostring(response) .. ': ' .. path, 2)
	end
end

readfile = function(path)
	assert(type(path) == 'string', "invalid argument #1 to 'readfile' (string expected, got " .. type(path) .. ')', 2)
	local response = send_method('readfile', path)
	if response == 'fail' or response == 'bad request' then
		error('FunnyExecutor -- readfile: cannot read: ' .. path, 2)
	end
	return base64decode(response)
end

isfile = function(path)
	assert(type(path) == 'string', "invalid argument #1 to 'isfile' (string expected, got " .. type(path) .. ')', 2)
	local response = send_method('isfile', path)
	return response == 'true'
end

isfolder = function(path)
	assert(type(path) == 'string', "invalid argument #1 to 'isfolder' (string expected, got " .. type(path) .. ')', 2)
	local response = send_method('isfolder', path)
	return response == 'true'
end

delfile = function(path)
	assert(type(path) == 'string', "invalid argument #1 to 'delfile' (string expected, got " .. type(path) .. ')', 2)
	local response = send_method('delfile', path)
	if response ~= 'ok' then
		error('FunnyExecutor -- delfile: cannot delete: ' .. path, 2)
	end
end

delfolder = function(path)
	assert(type(path) == 'string', "invalid argument #1 to 'delfolder' (string expected, got " .. type(path) .. ')', 2)
	local response = send_method('delfolder', path)
	if response ~= 'ok' then
		error('FunnyExecutor -- delfolder: cannot delete: ' .. path, 2)
	end
end

makefolder = function(path)
	assert(type(path) == 'string', "invalid argument #1 to 'makefolder' (string expected, got " .. type(path) .. ')', 2)
	local response = send_method('makefolder', path)
	if response ~= 'ok' then
		error('FunnyExecutor -- makefolder: ' .. tostring(response) .. ': ' .. path, 2)
	end
end

listfiles = function(path)
	local response = send_method('listfiles', path)
	if response == 'fail' or response == 'bad request' then
		error('FunnyExecutor -- listfiles: folder not found: ' .. tostring(path), 2)
	end
	if response == '' then
		return {}
	end
	return response:split('\n')
end

-- loadfile

loadfile = function(path: string)
	local ok, content = pcall(readfile, path)
	if not ok or content == nil then
		return nil, 'FunnyExecutor -- loadfile: unable to read \'' .. tostring(path) .. '\''
	end

	local ok2, result = pcall(loadstring, content)
	if not ok2 or result == nil then
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
	if not response or response == 'fail' or response == 'nil' then
		return nil
	end
	return base64decode(response)
end

dumpstring = getscriptbytecode

getscripthash = function(script)
	assert(typeof(script) == 'Instance' and script:IsA('LuaSourceContainer'), "invalid argument #1 to 'getscripthash' (LuaSourceContainer expected, got " .. typeof(script) .. ')', 2)

	local response = pointer_request('getscripthash', script)
	if not response or response == 'fail' or response == 'nil' then
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
	keypress = 'keyclick',
	keyrelease = 'keyrelease',
	mousescroll = 'mousescroll',
}

local env = getfenv()
for name, method in input_methods do
	env[name] = function(...)
		local response = send_method(method, ...)
		if response == 'fail' then
			warn('FunnyExecutor -- input error: ' .. name)
		end
	end
end

setrbxclipboard = setclipboard

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
isgameactive = iswindowactive

messagebox = function(text, title, flags)
	local response = send_method('messagebox', base64encode(tostring(text)), base64encode(tostring(title or 'FunnyExecutor')), tostring(flags or 0))
	return tonumber(response)
end

-- identifyexecutor

identifyexecutor = function()
	return 'FunnyExecutor', 'v0.350'
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
setmetatable(clonerefs, {__mode = 'v'})

local function clone_target(proxy)
	local obj = clonerefs[proxy]
	if obj == nil then
		error('cloneref target is no longer valid', 3)
	end
	return obj
end

cloneref = function(obj)
	local proxy = newproxy(true)
	local meta = getmetatable(proxy)
	clonerefs[proxy] = obj
	meta.__index = function(t, n)
		local o = clone_target(t)
		local v = o[n]
		if typeof(v) == 'function' then
			return function(self, ...)
				if self == t then
					self = o
				end
				return v(self, ...)
			end
		end
		return v
	end
	meta.__newindex = function(t, n, v)
		clone_target(t)[n] = v
	end
	meta.__tostring = function(t)
		return tostring(clone_target(t))
	end
	meta.__metatable = getmetatable(obj)
	return proxy
end

local function is_instance_like(v)
	if type(v) == 'userdata' then
		return true
	end
	if type(v) == 'table' then
		local mt = getmetatable(v)
		if type(mt) == 'table' and rawget(mt, '__funnyinstance') then
			return true
		end
	end
	return false
end

compareinstances = function(a, b)
	assert(is_instance_like(a), "invalid argument #1 to 'compareinstances' (Instance expected, got " .. typeof(a) .. ')', 2)
	assert(is_instance_like(b), "invalid argument #2 to 'compareinstances' (Instance expected, got " .. typeof(b) .. ')', 2)
	if clonerefs[a] then
		a = clonerefs[a]
	end
	if clonerefs[b] then
		b = clonerefs[b]
	end
	return a == b
end

local rtypeof = typeof
typeof = function(obj)
	if clonerefs[obj] then
		return 'Instance'
	end
	return rtypeof(obj)
end

local bootstrap_getnamecallmethod = getnamecallmethod

getnamecallmethod = function()
	if bootstrap_getnamecallmethod then
		local ok, registered = pcall(bootstrap_getnamecallmethod)
		if ok and registered then
			return registered
		end
	end
	return nil
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
		screen_gui.IgnoreGuiInset = true
		screen_gui.Parent = game:GetService('CoreGui')
		return screen_gui
	end)

	if ok then
		hidden_ui = gui
	end

	return hidden_ui
end

local drawing_objects = setmetatable({}, {__mode = 'k'})

local drawing_gui = nil

local function drawing_container()
	if drawing_gui and drawing_gui.Parent then
		return drawing_gui
	end

	local ok, gui = pcall(function()
		local screen_gui = Instance.new('ScreenGui')
		screen_gui.Name = 'DrawingGuis'
		screen_gui.ResetOnSpawn = false
		screen_gui.DisplayOrder = 999998
		screen_gui.IgnoreGuiInset = true
		screen_gui.Parent = game:GetService('CoreGui')
		return screen_gui
	end)

	if ok then
		drawing_gui = gui
	end

	return drawing_gui or gethui()
end

local function safe_font(name)
	local ok, font = pcall(function()
		return Enum.Font[name]
	end)
	if ok and font then
		return font
	end
	return Enum.Font.SourceSans
end

local draw_fonts = {
	[0] = safe_font('SourceSans'),
	[1] = safe_font('SourceSansBold'),
	[2] = safe_font('Plex'),
	[3] = safe_font('Code'),
}

local function resolve_font(font)
	if type(font) == 'number' then
		return draw_fonts[font] or Enum.Font.SourceSans
	elseif type(font) == 'string' then
		local ok, resolved = pcall(function()
			return Enum.Font[font]
		end)
		if ok and resolved then
			return resolved
		end
		return Enum.Font.SourceSans
	end
	return font or Enum.Font.SourceSans
end

local function draw_alpha(transparency)
	return math.clamp(1 - transparency, 0, 1)
end

local function style_line_frame(frame, state)
	frame.BorderSizePixel = 0
	frame.AnchorPoint = Vector2.new(0.5, 0.5)
	frame.BackgroundColor3 = state.Color
	frame.BackgroundTransparency = draw_alpha(state.Transparency)
	frame.ZIndex = state.ZIndex
	frame.Visible = state.Visible
end

local function place_line_frame(frame, from, to, thickness)
	local delta = to - from
	local length = delta.Magnitude
	frame.Position = UDim2.fromOffset((from.X + to.X) / 2, (from.Y + to.Y) / 2)
	frame.Size = UDim2.fromOffset(length, thickness)
	frame.Rotation = math.deg(math.atan(delta.Y, delta.X))
end

local function place_edge_frame(frame, p1, p2, opposite)
	local delta = p2 - p1
	local length = delta.Magnitude
	local nx, ny = -delta.Y, delta.X
	local nlen = math.sqrt(nx * nx + ny * ny)
	if nlen == 0 then
		frame.Visible = false
		return
	end
	local ux, uy = nx / nlen, ny / nlen
	local mid = (p1 + p2) / 2
	local rel = opposite - mid
	local dist = rel.X * ux + rel.Y * uy
	frame.Position = UDim2.fromOffset(mid.X + ux * dist / 2, mid.Y + uy * dist / 2)
	frame.Size = UDim2.fromOffset(length, math.abs(dist))
	frame.Rotation = math.deg(math.atan(delta.Y, delta.X))
end

local function draw_defaults(class)
	local state = {
		Visible = false,
		Color = Color3.new(1, 1, 1),
		Transparency = 1,
		ZIndex = 0,
		__OBJECT_EXISTS = true,
	}
	if class == 'Line' then
		state.From = Vector2.zero
		state.To = Vector2.zero
		state.Thickness = 1
	elseif class == 'Square' then
		state.Position = Vector2.zero
		state.Size = Vector2.zero
		state.Thickness = 1
		state.Filled = false
	elseif class == 'Circle' then
		state.Position = Vector2.zero
		state.Radius = 0
		state.Thickness = 1
		state.Filled = false
		state.NumSides = 30
	elseif class == 'Text' then
		state.Text = ''
		state.Size = 13
		state.Center = false
		state.Outline = false
		state.OutlineColor = Color3.new(0, 0, 0)
		state.Position = Vector2.zero
		state.Font = 0
	elseif class == 'Image' then
		state.Url = ''
		state.Data = ''
		state.Position = Vector2.zero
		state.Size = Vector2.zero
		state.Rounding = 0
	elseif class == 'Triangle' then
		state.PointA = Vector2.zero
		state.PointB = Vector2.zero
		state.PointC = Vector2.zero
		state.Thickness = 1
		state.Filled = false
	elseif class == 'Quad' then
		state.PointA = Vector2.zero
		state.PointB = Vector2.zero
		state.PointC = Vector2.zero
		state.PointD = Vector2.zero
		state.Thickness = 1
		state.Filled = false
	end
	return state
end

local draw_builders = {}

draw_builders.Line = function(entry)
	local frame = Instance.new('Frame')
	frame.Visible = false
	frame.Parent = drawing_container()
	table.insert(entry.instances, frame)

	entry.apply = function()
		local state = entry.state
		style_line_frame(frame, state)
		place_line_frame(frame, state.From, state.To, state.Thickness)
	end
end

draw_builders.Square = function(entry)
	local frame = Instance.new('Frame')
	frame.Visible = false
	local stroke = Instance.new('UIStroke')
	stroke.Enabled = false
	stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	stroke.Parent = frame
	frame.Parent = drawing_container()
	table.insert(entry.instances, frame)

	entry.apply = function()
		local state = entry.state
		frame.BackgroundColor3 = state.Color
		frame.Position = UDim2.fromOffset(state.Position.X, state.Position.Y)
		frame.Size = UDim2.fromOffset(state.Size.X, state.Size.Y)
		frame.ZIndex = state.ZIndex
		frame.Visible = state.Visible
		if state.Filled then
			frame.BackgroundTransparency = draw_alpha(state.Transparency)
			stroke.Enabled = false
		else
			frame.BackgroundTransparency = 1
			stroke.Enabled = true
			stroke.Color = state.Color
			stroke.Thickness = state.Thickness
			stroke.Transparency = draw_alpha(state.Transparency)
		end
	end
end

draw_builders.Circle = function(entry)
	local frame = Instance.new('Frame')
	frame.Visible = false
	frame.AnchorPoint = Vector2.new(0.5, 0.5)
	local corner = Instance.new('UICorner')
	corner.CornerRadius = UDim.new(1, 0)
	corner.Parent = frame
	local stroke = Instance.new('UIStroke')
	stroke.Enabled = false
	stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	stroke.Parent = frame
	frame.Parent = drawing_container()
	table.insert(entry.instances, frame)

	entry.apply = function()
		local state = entry.state
		frame.BackgroundColor3 = state.Color
		frame.Position = UDim2.fromOffset(state.Position.X, state.Position.Y)
		frame.Size = UDim2.fromOffset(state.Radius * 2, state.Radius * 2)
		frame.ZIndex = state.ZIndex
		frame.Visible = state.Visible
		if state.Filled then
			frame.BackgroundTransparency = draw_alpha(state.Transparency)
			stroke.Enabled = false
		else
			frame.BackgroundTransparency = 1
			stroke.Enabled = true
			stroke.Color = state.Color
			stroke.Thickness = state.Thickness
			stroke.Transparency = draw_alpha(state.Transparency)
		end
	end
end

draw_builders.Text = function(entry)
	local label = Instance.new('TextLabel')
	label.Visible = false
	label.BackgroundTransparency = 1
	label.BorderSizePixel = 0
	label.AutomaticSize = Enum.AutomaticSize.XY
	label.Size = UDim2.new(0, 0, 0, 0)
	local stroke = Instance.new('UIStroke')
	stroke.Enabled = false
	stroke.Thickness = 2
	stroke.Parent = label
	label.Parent = drawing_container()
	table.insert(entry.instances, label)

	entry.apply = function()
		local state = entry.state
		label.Text = state.Text
		label.TextColor3 = state.Color
		label.TextTransparency = draw_alpha(state.Transparency)
		label.TextSize = state.Size
		label.Font = resolve_font(state.Font)
		label.AnchorPoint = Vector2.new(state.Center and 0.5 or 0, state.Center and 0.5 or 0)
		label.Position = UDim2.fromOffset(state.Position.X, state.Position.Y)
		label.ZIndex = state.ZIndex
		label.Visible = state.Visible
		stroke.Enabled = state.Outline
		stroke.Color = state.OutlineColor
	end
end

draw_builders.Image = function(entry)
	local image = Instance.new('ImageLabel')
	image.Visible = false
	image.BackgroundTransparency = 1
	image.Parent = drawing_container()
	table.insert(entry.instances, image)

	entry.apply = function()
		local state = entry.state
		image.Image = state.Url ~= '' and state.Url or state.Data
		image.ImageColor3 = state.Color
		image.ImageTransparency = draw_alpha(state.Transparency)
		image.Position = UDim2.fromOffset(state.Position.X, state.Position.Y)
		image.Size = UDim2.fromOffset(state.Size.X, state.Size.Y)
		image.ZIndex = state.ZIndex
		image.Visible = state.Visible
	end
end

local function build_polygon(entry, points)
	for _ = 1, #points * 2 do
		local frame = Instance.new('Frame')
		frame.Visible = false
		frame.Parent = drawing_container()
		table.insert(entry.instances, frame)
	end

	entry.apply = function()
		local state = entry.state
		local n = #points

		for _, inst in entry.instances do
			inst.Visible = false
		end

		if state.Filled then
			for i = 1, n do
				local a = state[points[i]]
				local b = state[points[i % n + 1]]
				local c = state[points[(i + 1) % n + 1]]
				local frame = entry.instances[n + i]
				style_line_frame(frame, state)
				place_edge_frame(frame, a, b, c)
			end
		else
			for i = 1, n do
				local a = state[points[i]]
				local b = state[points[i % n + 1]]
				local frame = entry.instances[i]
				style_line_frame(frame, state)
				place_line_frame(frame, a, b, state.Thickness)
			end
		end
	end
end

draw_builders.Triangle = function(entry)
	build_polygon(entry, {'PointA', 'PointB', 'PointC'})
end

draw_builders.Quad = function(entry)
	build_polygon(entry, {'PointA', 'PointB', 'PointC', 'PointD'})
end

Drawing = {}

function Drawing.new(class, properties)
	assert(type(class) == 'string', "invalid argument #1 to 'Drawing.new' (string expected, got " .. type(class) .. ')', 2)
	local builder = draw_builders[class]
	assert(builder, "invalid argument #1 to 'Drawing.new' (Line, Text, Image, Square, Quad, Circle or Triangle expected, got '" .. tostring(class) .. "')", 2)

	local entry = {
		class = class,
		state = draw_defaults(class),
		instances = {},
	}

	builder(entry)
	entry.apply()

	local proxy = newproxy(true)
	local meta = getmetatable(proxy)

	meta.__index = function(_, key)
		if key == 'Remove' or key == 'Destroy' then
			return entry.remove
		end
		if entry.state[key] ~= nil then
			return entry.state[key]
		end
		if key == 'TextBounds' and class == 'Text' then
			return entry.instances[1].TextBounds
		end
		error(tostring(key) .. ' is not a valid member of Drawing (' .. class .. ')', 2)
	end

	meta.__newindex = function(_, key, value)
		assert(entry.state[key] ~= nil, tostring(key) .. ' is not a valid member of Drawing (' .. class .. ')', 2)
		entry.state[key] = value
		entry.apply()
	end

	meta.__tostring = function()
		return 'Drawing (' .. class .. ')'
	end

	entry.remove = function()
		for _, inst in entry.instances do
			pcall(function()
				inst:Destroy()
			end)
		end
		entry.instances = {}
		drawing_objects[proxy] = nil
	end

	drawing_objects[proxy] = entry

	if type(properties) == 'table' then
		for key, value in properties do
			proxy[key] = value
		end
	end

	return proxy
end

Drawing.Fonts = {
	UI = 0,
	System = 1,
	Plex = 2,
	Monospace = 3,
}

isrenderobj = function(object)
	return drawing_objects[object] ~= nil
end

cleardrawcache = function()
	for proxy in drawing_objects do
		local entry = drawing_objects[proxy]
		if entry then
			entry.remove()
		end
	end
end

isrenderavailable = function()
	return true
end

getrenderproperty = function(drawing, property)
	local entry = drawing_objects[drawing]
	assert(entry, "invalid argument #1 to 'getrenderproperty' (Drawing expected)", 2)
	assert(type(property) == 'string', "invalid argument #2 to 'getrenderproperty' (string expected, got " .. type(property) .. ')', 2)
	return drawing[property]
end

setrenderproperty = function(drawing, property, value)
	local entry = drawing_objects[drawing]
	assert(entry, "invalid argument #1 to 'setrenderproperty' (Drawing expected)", 2)
	assert(type(property) == 'string', "invalid argument #2 to 'setrenderproperty' (string expected, got " .. type(property) .. ')', 2)
	drawing[property] = value
end

local instance_registry = {}

local function register_instance(inst)
	instance_registry[inst] = true
end

local function registry_entries()
	local entries = {}
	local key = nil
	while true do
		local ok, next_key = pcall(next, instance_registry, key)
		if not ok or next_key == nil then
			break
		end
		entries[#entries + 1] = next_key
		key = next_key
	end
	return entries
end

local function all_known_instances()
	local result, seen = {}, {}
	local function add(inst)
		if inst ~= nil and not seen[inst] then
			seen[inst] = true
			result[#result + 1] = inst
		end
	end
	pcall(function()
		for _, inst in game:GetDescendants() do
			add(inst)
		end
	end)
	for _, inst in ipairs(registry_entries()) do
		local okt, is_inst = pcall(typeof, inst)
		if okt and is_inst == 'Instance' then
			add(inst)
		end
	end
	return result
end

local real_Instance = Instance
Instance = setmetatable({
	new = function(class, parent)
		local inst = real_Instance.new(class)
		register_instance(inst)
		if parent ~= nil then
			pcall(function()
				inst.Parent = parent
			end)
		end
		return inst
	end,
}, {__index = real_Instance})

game.DescendantAdded:Connect(register_instance)

getinstances = function()
	return all_known_instances()
end

getnilinstances = function()
	local result = {}
	for _, inst in ipairs(registry_entries()) do
		local okt, is_inst = pcall(typeof, inst)
		if okt and is_inst == 'Instance' then
			local ok, parent = pcall(function()
				return inst.Parent
			end)
			if ok and parent == nil then
				result[#result + 1] = inst
			end
		end
	end
	return result
end

local function is_client_script(inst)
	local ok, res = pcall(function()
		if inst:IsA('LocalScript') or inst:IsA('ModuleScript') then
			return true
		end
		if inst.ClassName == 'Script' then
			return inst.RunContext == Enum.RunContext.Client
		end
		return false
	end)
	return ok and res == true
end

getscripts = function()
	local result, seen = {}, {}
	local function add(inst)
		if inst ~= nil and not seen[inst] and is_client_script(inst) then
			seen[inst] = true
			result[#result + 1] = inst
		end
	end
	pcall(function()
		for _, inst in game:GetDescendants() do
			add(inst)
		end
	end)
	for _, inst in ipairs(registry_entries()) do
		add(inst)
	end
	return result
end

getrunningscripts = function()
	local result = {}
	for _, inst in ipairs(getscripts()) do
		local ok, running = pcall(function()
			if inst.Parent == nil then
				return false
			end
			local full_name = inst:GetFullName()
			if full_name:find('CoreGui', 1, true) or full_name:find('CorePackages', 1, true) then
				return false
			end
			local oke, enabled = pcall(function()
				return inst.Enabled
			end)
			if oke and enabled == false then
				return false
			end
			return inst:FindFirstAncestorOfClass('Actor') == nil
		end)
		if ok and running then
			result[#result + 1] = inst
		end
	end
	return result
end

local loaded_modules = setmetatable({}, {__mode = 'k'})

local function module_env(mod)
	return setmetatable({script = mod, require = require}, {__index = getfenv()})
end

require = function(mod)
	assert(typeof(mod) == 'Instance', "invalid argument #1 to 'require' (ModuleScript expected, got " .. typeof(mod) .. ')', 2)
	local okm, ism = pcall(function()
		return mod:IsA('ModuleScript')
	end)
	if not okm or not ism then
		error("invalid argument #1 to 'require' (ModuleScript expected, got " .. typeof(mod) .. ')', 2)
	end

	if loaded_modules[mod] ~= nil then
		return loaded_modules[mod]
	end

	local bytecode = getscriptbytecode(mod)
	if not bytecode or #bytecode == 0 then
		error('require: failed to get bytecode for ' .. tostring(mod), 2)
	end

	local chunk = load_bytecode(bytecode, module_env(mod))
	local result = chunk()
	loaded_modules[mod] = result
	return result
end

getloadedmodules = function()
	local result = {}
	for mod in pairs(loaded_modules) do
		result[#result + 1] = mod
	end
	return result
end

getscriptclosure = function(script_inst)
	assert(typeof(script_inst) == 'Instance' and script_inst:IsA('LuaSourceContainer'), "invalid argument #1 to 'getscriptclosure' (LuaSourceContainer expected, got " .. typeof(script_inst) .. ')', 2)
	local bytecode = getscriptbytecode(script_inst)
	if not bytecode or #bytecode == 0 then
		return nil
	end
	return load_bytecode(bytecode, module_env(script_inst))
end

getscriptfunction = getscriptclosure

getsenv = function(script_inst)
	assert(typeof(script_inst) == 'Instance' and script_inst:IsA('LuaSourceContainer'), "invalid argument #1 to 'getsenv' (LuaSourceContainer expected, got " .. typeof(script_inst) .. ')', 2)
	local oke, enabled = pcall(function()
		return script_inst.Enabled
	end)
	if script_inst:IsA('LocalScript') and oke and enabled == false then
		error('getsenv: script is not running', 2)
	end
	return module_env(script_inst)
end

getcallingscript = function()
	return nil
end

-- isreadonly

isreadonly = function(tbl)
	assert(type(tbl) == 'table', "invalid argument #1 to 'isreadonly' (table expected, got " .. type(tbl) .. ')', 2)
	return table.isfrozen(tbl)
end

-- cache (service refs swap through the bootstrap GetService cache)

local invalidated = setmetatable({}, {__mode = 'k'})

local function find_service_name(inst)
	local sc = rawget(getfenv(), '__funny_service_cache')
	if type(sc) ~= 'table' then
		return nil
	end
	for name, service in pairs(sc) do
		if service == inst then
			return name
		end
	end
	return nil
end

cache = {}

cache.invalidate = function(inst)
	assert(typeof(inst) == 'Instance', "invalid argument #1 to 'cache.invalidate' (Instance expected, got " .. typeof(inst) .. ')', 2)
	invalidated[inst] = true
	local name = find_service_name(inst)
	local sc = rawget(getfenv(), '__funny_service_cache')
	if name and type(sc) == 'table' then
		sc[name] = cloneref(inst)
	end
end

cache.iscached = function(inst)
	assert(typeof(inst) == 'Instance', "invalid argument #1 to 'cache.iscached' (Instance expected, got " .. typeof(inst) .. ')', 2)
	return invalidated[inst] ~= true
end

cache.replace = function(inst, replacement)
	assert(typeof(inst) == 'Instance', "invalid argument #1 to 'cache.replace' (Instance expected, got " .. typeof(inst) .. ')', 2)
	assert(typeof(replacement) == 'Instance', "invalid argument #2 to 'cache.replace' (Instance expected, got " .. typeof(replacement) .. ')', 2)
	local name = find_service_name(inst)
	local sc = rawget(getfenv(), '__funny_service_cache')
	if name and type(sc) == 'table' then
		sc[name] = cloneref(replacement)
	end
end

local queue_file = 'queued_teleports.lua'
local queue_marker = '\n--__FUNNYQUEUE__--\n'

queue_on_teleport = function(source)
	assert(type(source) == 'string', "invalid argument #1 to 'queue_on_teleport' (string expected, got " .. type(source) .. ')', 2)

	local ok, existing = pcall(readfile, queue_file)
	if not ok or not existing or existing == '' then
		pcall(writefile, queue_file, source)
	else
		pcall(writefile, queue_file, existing .. queue_marker .. source)
	end
end

queueonteleport = queue_on_teleport

clearqueueonteleport = function()
	pcall(delfile, queue_file)
end
clearteleportqueue = clearqueueonteleport
clear_teleport_queue = clearqueueonteleport

local function flush_teleport_queue()
	if not isfile(queue_file) then
		return
	end

	local ok, content = pcall(readfile, queue_file)
	if not ok or not content then
		return
	end
	pcall(delfile, queue_file)

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

isnetworkowner = function(part: BasePart)
	if part.Anchored or part:IsGrounded() or not part or not part:IsA("BasePart") then
		return false
	end
	return part.ReceiveAge == 0
end

firetouchinterest = function(part, otherPart, endTouched)
	assert(typeof(part) == 'Instance', "invalid argument #1 to 'firetouchinterest' (BasePart expected, got " .. typeof(part) .. ')', 2)
	assert(typeof(otherPart) == 'Instance', "invalid argument #2 to 'firetouchinterest' (BasePart expected, got " .. typeof(otherPart) .. ')', 2)
	pcall(function()
		if endTouched then
			otherPart.CFrame = otherPart.CFrame * CFrame.new(0, -60, 0)
		else
			otherPart.CFrame = part.CFrame
		end
	end)
end

getcallbackvalue = function(inst, property)
	assert(typeof(inst) == 'Instance', "invalid argument #1 to 'getcallbackvalue' (Instance expected, got " .. typeof(inst) .. ')', 2)
	assert(type(property) == 'string', "invalid argument #2 to 'getcallbackvalue' (string expected, got " .. type(property) .. ')', 2)
	local ok, value = pcall(function()
		return inst[property]
	end)
	if ok and type(value) == 'function' then
		return value
	end
	return nil
end

request = function(options)
	assert(type(options) == 'table' and type(options.Url) == 'string', "invalid argument #1 to 'request' (table with Url expected, got " .. type(options) .. ')', 2)

	local headers = {}
	if type(options.Headers) == 'table' then
		for k, v in options.Headers do
			headers[k] = v
		end
	end

	if type(options.Cookies) == 'table' then
		local parts = {}
		for k, v in options.Cookies do
			parts[#parts + 1] = tostring(k) .. '=' .. tostring(v)
		end
		if #parts > 0 then
			local joined = table.concat(parts, '; ')
			local existing = headers['Cookie'] or headers['cookie']
			headers['Cookie'] = existing and (existing .. '; ' .. joined) or joined
		end
	end

	local result = nil

	http:RequestInternal({
		Url = options.Url,
		Method = options.Method or "GET",
		Headers = headers,
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
env.http = {request = request}
syn = {request = request}

Signal = {}

function Signal.new()
	local handlers = {}
	local waiting = {}

	local signal = {}

	local function fire(...)
		local snapshot = table.clone(handlers)
		for _, entry in ipairs(snapshot) do
			task.spawn(entry.fn, ...)
		end
		local threads = waiting
		waiting = {}
		for _, thread in ipairs(threads) do
			task.spawn(thread, ...)
		end
	end

	function signal:Connect(fn)
		assert(type(fn) == 'function', "invalid argument #1 to 'Connect' (function expected, got " .. type(fn) .. ')', 2)
		local entry = {fn = fn}
		table.insert(handlers, entry)

		local connection = {}
		function connection:Disconnect()
			local idx = table.find(handlers, entry)
			if idx then
				table.remove(handlers, idx)
			end
		end

		return connection
	end

	function signal:Once(fn)
		assert(type(fn) == 'function', "invalid argument #1 to 'Once' (function expected, got " .. type(fn) .. ')', 2)
		local connection
		connection = self:Connect(function(...)
			connection:Disconnect()
			fn(...)
		end)
		return connection
	end

	function signal:Wait()
		local thread = coroutine.running()
		table.insert(waiting, thread)
		return coroutine.yield()
	end

	function signal:Fire(...)
		fire(...)
	end

	return signal
end

local function rconsole_bridge(method, text)
	local response = send_method(method, base64encode(tostring(text)))
	if response ~= 'ok' then
		warn('FunnyExecutor -- rconsole error: ' .. tostring(response))
	end
end

rconsoleprint = function(text) rconsole_bridge('rconsoleprint', text) end
rconsoleinfo = function(text) rconsole_bridge('rconsoleinfo', text) end
rconsolewarn = function(text) rconsole_bridge('rconsolewarn', text) end
rconsoleerr = function(text) rconsole_bridge('rconsoleerr', text) end
rconsoleclear = function() send_method('rconsoleclear') end
rconsoleshow = function() send_method('rconsoleshow') end
rconsolehide = function() send_method('rconsolehide') end
rconsolename = function(name) rconsole_bridge('rconsolename', name) end
rconsoleinput = function()
	local response = send_method('rconsoleinput')
	if not response or response == '' then
		return ''
	end
	local ok, decoded = pcall(base64decode, response)
	return ok and decoded or ''
end

local function dialog_request(method_name, options)
	local payload = '{}'
	pcall(function()
		payload = http:JSONEncode(type(options) == 'table' and options or {})
	end)
	local response = send_method(method_name, base64encode(payload))
	if not response or response == '' then
		return nil
	end
	local ok, decoded = pcall(base64decode, response)
	return ok and decoded or nil
end

openfiledialog = function(options) return dialog_request('openfiledialog', options) end
savefiledialog = function(options) return dialog_request('savefiledialog', options) end
openfolderdialog = function(options) return dialog_request('openfolderdialog', options) end
openfilesdialog = function(options)
	local paths = dialog_request('openfilesdialog', options)
	if not paths or paths == '' then
		return {}
	end
	return paths:split('\n')
end

local thread_identities = setmetatable({}, {__mode = 'k'})

getthreadidentity = function()
	return thread_identities[coroutine.running()] or 2
end

setthreadidentity = function(identity)
	assert(type(identity) == 'number', "invalid argument #1 to 'setthreadidentity' (number expected, got " .. type(identity) .. ')', 2)
	thread_identities[coroutine.running()] = math.floor(identity)
end

getidentity = getthreadidentity
getthreadcontext = getthreadidentity
setidentity = setthreadidentity
setthreadcontext = setthreadidentity

getactors = function()
	local result = {}
	for _, inst in ipairs(all_known_instances()) do
		local ok, is_actor = pcall(function()
			return inst:IsA('Actor')
		end)
		if ok and is_actor then
			result[#result + 1] = inst
		end
	end
	return result
end

isparallel = function()
	return false
end

run_on_actor = function(actor, source, ...)
	assert(typeof(actor) == 'Instance', "invalid argument #1 to 'run_on_actor' (Actor expected, got " .. typeof(actor) .. ')', 2)
	assert(type(source) == 'string', "invalid argument #2 to 'run_on_actor' (string expected, got " .. type(source) .. ')', 2)
	local args = table.pack(...)
	task.spawn(function()
		local func, err = loadstring(source)
		if func then
			local ok, run_err = pcall(func, table.unpack(args, 1, args.n))
			if not ok then
				warn('FunnyExecutor -- run_on_actor: ' .. tostring(run_err))
			end
		else
			warn('FunnyExecutor -- run_on_actor: ' .. tostring(err))
		end
	end)
end

local comm_channels = {}
local comm_counter = 0

local function make_comm_channel()
	comm_counter += 1
	local bindable = Instance.new('BindableEvent')
	local object = {
		Event = bindable.Event,
		Fire = function(_, ...)
			bindable:Fire(...)
		end,
	}
	comm_channels[comm_counter] = object
	return comm_counter, object
end

create_comm_channel = make_comm_channel

get_comm_channel = function(id)
	assert(type(id) == 'number', "invalid argument #1 to 'get_comm_channel' (number expected, got " .. type(id) .. ')', 2)
	return comm_channels[id]
end

get_hidden_gui = gethui
clonereference = cloneref

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