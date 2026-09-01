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

local function namecall_handler(method, self, ...)
	if typeof(self) ~= "table" then
		return false
	end

	local mt = getmetatable(self)
	local nc = type(mt) == "table" and rawget(mt, "__namecall")
	if type(nc) == "function" and debug.info(nc, 's') then
		namecall_registry[coroutine.running()] = method
		return true, nc(self, ...)
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
