local http = game:GetService("HttpService")
local bridge = "http://localhost:9475"

local function bridge_request(method)
	local result = nil

	local ok = pcall(function()
		http:RequestInternal({
			Url = bridge,
			Method = "POST",
			Body = method,
			Headers = {
				["Content-Type"] = "text/plain"
			}
		}):Start(function(s, b)
			result = b
			result["Success"] = s
		end)
	end)

	if not ok then
		return nil
	end

	repeat task.wait() until result

	if not result or not result.Success then
		return nil
	end

	return result.Body
end

local namecall_registry = setmetatable({}, {__mode = "k"})

-- set by init.luau (cache.invalidate / cache.replace), checked on game:GetService
local service_cache = {}
__funny_service_cache = service_cache

local function http_get(url)
	local result = nil

	local ok = pcall(function()
		http:RequestInternal({
			Url = url,
			Method = "GET",
			Headers = {
				["Content-Type"] = "text/plain"
			}
		}):Start(function(s, b)
			result = b
			result["Success"] = s
		end)
	end)

	if not ok then
		error("HttpGet: RequestInternal unavailable", 0)
	end

	repeat task.wait() until result

	if not result or not result.Success then
		error("HttpGet: request failed for " .. tostring(url), 0)
	end

	return result.Body
end

local function namecall_handler(method, self, ...)
	namecall_registry[coroutine.running()] = method

	if typeof(self) == "table" then
		local mt = getmetatable(self)
		local nc = type(mt) == "table" and rawget(mt, "__namecall")
		if type(nc) == "function" and debug.info(nc, 's') then
			return true, nc(self, ...)
		end
		return false
	end

	if self == game then
		if method == "HttpGet" or method == "HttpGetAsync" then
			return true, http_get(...)
		elseif method == "GetService" then
			local name = ...
			local cached = service_cache[name]
			if cached ~= nil then
				return true, cached
			end
			local ok, service = pcall(function()
				return game:GetService(name)
			end)
			if ok and service then
				service_cache[name] = service
				return true, service
			end
		end
	end

	return false
end

getnamecallmethod = function()
	return namecall_registry[coroutine.running()]
end

load_bytecode = function(bytecode, env)
	local settings = fiu.luau_newsettings()
	settings.vectorCtor = Vector3.new
	settings.useNativeNamecall = true
	settings.namecallHandler = namecall_handler

	return (fiu.luau_load(bytecode, env or getfenv(), settings))
end

task.spawn(function()
	while true do
		local bytecode = bridge_request("getinitraw")

		if bytecode then
			local ok, func = pcall(load_bytecode, bytecode, getfenv())

			if ok and func then
				local ran, err = pcall(func)

				if not ran then
					warn("FunnyExecutor bootstrap: init.luau error: " .. tostring(err))
				end

				break
			elseif ok then
				warn("FunnyExecutor bootstrap: init.luau failed to load (bridge/bytecode mismatch?)")
			else
				warn("FunnyExecutor bootstrap: " .. tostring(func))
			end
		end

		task.wait(2)
	end
end)

return setmetatable({}, {
	__index = function()
		return function() end
	end
})
