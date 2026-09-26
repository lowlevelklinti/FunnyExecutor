local MarketplaceService = game:GetService("MarketplaceService")
local HttpService = game:GetService("HttpService")

local bridgeUrl = 'http://127.0.0.1:9475'

local b64encode = base64encode or function(data)
    local b = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    local result = {}
    local len = #data
    for i = 1, len, 3 do
        local a = string.byte(data, i)
        local b = string.byte(data, i + 1) or 0
        local c = string.byte(data, i + 2) or 0
        local n = a * 65536 + b * 256 + c
        table.insert(result, string.sub(b, math.floor(n / 262144) % 64 + 1, math.floor(n / 262144) % 64 + 1))
        table.insert(result, string.sub(b, math.floor(n / 4096) % 64 + 1, math.floor(n / 4096) % 64 + 1))
        if i + 1 <= len then
            table.insert(result, string.sub(b, math.floor(n / 64) % 64 + 1, math.floor(n / 64) % 64 + 1))
        else
            table.insert(result, '=')
        end
        if i + 2 <= len then
            table.insert(result, string.sub(b, n % 64 + 1, n % 64 + 1))
        else
            table.insert(result, '=')
        end
    end
    return table.concat(result)
end

local lastPlaceId = 0
local lastSendTime = 0

local function sendGameInfo(force)
    local placeId = game.PlaceId
    if not placeId or placeId <= 0 then
        return
    end

    local now = os.clock()
    local changed = placeId ~= lastPlaceId

    if not force and not changed and (now - lastSendTime) < 15 then
        return
    end

    local info = MarketplaceService:GetProductInfo(placeId)
    local gameName = info and info.Name or 'Unknown Game'
    local creator = info and info.Creator and info.Creator.Name or 'Unknown'

    local body = string.format("getgameinfo\n%s\n%s\n%s",
        b64encode(tostring(placeId)),
        b64encode(gameName),
        b64encode(creator)
    )

    pcall(function()
        HttpService:RequestInternal({
            Url = bridgeUrl,
            Method = "POST",
            Body = body,
            Headers = {
                ['Content-Type'] = "text/plain"
            }
        }):Start(function(success, response)
        end)
    end)

    lastPlaceId = placeId
    lastSendTime = now
end

task.spawn(function()
    sendGameInfo(true)
    while true do
        sendGameInfo(false)
        task.wait(5)
    end
end)
