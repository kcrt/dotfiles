
-- Script for HammerSpoon
-- Place this script at ~/.hammerspoon/init.lua

logger = hs.logger.new("kcrt", "debug")

function chomp(s)
	if s == "" then
		return ""
	end
	return s:gsub("\n$", "")
end

function normal_alert(s)
	hs.alert.show(s, hs.alert.defaultStyle, hs.screen.mainScreen(), 5)
	logger.i(s)
end

function warn_alert(s)
	local style = {}
	style.fillColor = {red=0.8, alpha=0.8}
	style.strokeColor = hs.drawing.color.definedCollections.hammerspoon.osx_yellow
	style.strokeWidth = 10
	style.fadeInDuration = 0.3
	hs.alert.show(s, style, hs.screen.mainScreen(), 10)
	logger.i(s)
end

function dump(o)
   if type(o) == 'table' then
      local s = '{ '
      for k,v in pairs(o) do
         if type(k) ~= 'number' then k = '"'..k..'"' end
         s = s .. '['..k..'] = ' .. dump(v) .. ','
      end
      return s .. '} '
   else
      return tostring(o)
   end
end

function isArray(t)
	local i = 0
	for _ in pairs(t) do
		i = i + 1
		if t[i] == nil then return false end
	end
	return true
end

-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
--   バッテリー
-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
-- function batteryWatcherCallback()
--	
-- end
-- batteryWatcher = hs.battery.watcher.new(batteryWatcherCallback)
-- batteryWatcher:start()


-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
--   USB 機器ごとに特定の動作を行う
-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
function onICRecorderNotify(data)
	local startRecorderTimer = hs.timer.doAfter(5, function()
		hs.application.open(os.getenv("HOME") .. "/Documents/Automators/DrainRecorder.app")
	end)
end
function onAmazonKindleNotify(data)
	hs.application.open("/Volumes/Kindle/")
end
function oniPhoneConnectionNotify(data)
	hs.application.open("/System/Applications/Photos.app")
end

function usbDeviceCallback(data)

	logger.i(data["productName"] .. " of " .. data["vendorName"] .. " was " .. data["eventType"])

	if (data["eventType"] == "added") then
		normal_alert("'" .. data["productName"] .. "' is connected.")
	elseif (data["eventType"] == "removed") then
		normal_alert("'" .. data["productName"] .. "' was disconnected.")
	end

	if (data["productName"] == "IC RECORDER" and data["eventType"] == "added") then
		hs.notify.new(onICRecorderNotify, {title="IC Recorder connected!", informativeText="Do you want to move recording file to local?", actionButtonTitle= "Move file", hasActionButton=true, withdrawAfter=30}):send()
	elseif (data["productName"] == "Amazon Kindle" and data["eventType"] == "added") then
		hs.notify.new(onAmazonKindleNotify, {title="Kindle connected!", informativeText="Do you want to open the Volume?", actionButtonTitle= "Open", hasActionButton=true}):send()
	elseif (data["productName"] == "ELECOM TrackBall Mouse" and data["eventType"] == "added") then
		-- Connected to the mother ship display
	elseif (data["productName"] == "iPhone" and data["eventType"] == "added") then
		hs.notify.new(oniPhoneConnectionNotify, {title="iPhone connected!", informativeText="Do you want to open the Photo.app?", actionButtonTitle= "Open", hasActionButton=true}):send()
	end

end

usbWatcher = hs.usb.watcher.new(usbDeviceCallback)
usbWatcher:start()

-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
--   キーボードチャタリングの防止
-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
inSuppress = false
function blockSpaceKeyChattering(e)
	if e:getKeyCode() ~= 49 then return false end
	if not inSuppress then
		inSuppress = true
		hs.timer.doAfter(0.18, function() inSuppress = false end)
		return false
	else
		logger.i("Space key chattering was suppressed!")
		return true
	end
end
if false then -- change to true to enable
	spSuppressor = hs.eventtap.new({hs.eventtap.event.types.keyDown}, blockSpaceKeyChattering)
	spSuppressor:start()
end

-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
--   Wi-Fi 監視
-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
lastssid = ""
lastplace = ""
lastSSIDTime = 0

function ssidChangedCallback(watcher, message, interface)

	ssid = hs.wifi.currentNetwork(interface)
	logger.i("WiFi event: " .. message .. " on " .. interface .. ", SSID: " .. tostring(ssid))

	if ssid == nil then
		if lastssid == "" then
			return false
		end
		normal_alert("Wifi disconnected")
		lastssid = ""
		removeInformationBar()
		return false
	else
		if os.time() - lastSSIDTime < 2 then
			-- 頻繁な切り替えを無視
			return false
		end
		lastSSIDTime = os.time()
		normal_alert("Connected to: " .. ssid .. " on " ..interface)
		updateTetheringBar(ssid)
	end

	if ssid == "nagakuranet" then
		-- nextmobile_handle = hs.timer.doAfter(10, CheckNextMobile)
		logger.i("Hook added for NextMobile.")
	elseif ssid == "nagakuranet2" then
		-- wimaxhome02_handle = hs.timer.doAfter(10, CheckWiMAXHome02)
		logger.i("Hook added for WiMAX Home2.")
	elseif string.sub(ssid, 1, 4) == "nano" then
		normal_alert("Welcome back to my home!")

		scansnap = hs.application.find("ScanSnap Manager")	
		if scansnap ~= nil then scansnap:kill() end

	elseif ssid == "UTokyo-WiFi" then

	end
	lastssid = ssid

end

wifiWatcher = hs.wifi.watcher.new(ssidChangedCallback)
wifiWatcher:start()

-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
--   ネットワーク管理
-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
function checkPing()
	function checkPingCallback(object, message, seqnum, error)
		if message == "didFinish" then
			avg = tonumber(string.match(object:summary(), '/(%d+.%d+)/'))
			if avg == 0.0 then
				normal_alert("No network")
			elseif avg < 30.0 then
				normal_alert("Network good (" .. avg .. "ms)")
			elseif avg < 100.0 then
				normal_alert("Network well (" .. avg .. "ms)")
			else
				warn_alert("Network bad (" .. avg .. "ms)")
			end
		end
	end
	local pingChecker = hs.network.ping.ping("8.8.8.8", 3, 1, 3, "any", checkPingCallback)
end
function reconnectEn5()

end
function CheckNetworkInterface()
	ipv4if, ipv6if = hs.network.primaryInterfaces()
	currentif = ipv4if
	checkPing()
	detail = hs.network.interfaceDetails(currentif)
	output, status, type_, rc = hs.execute('ifconfig | grep -A 10 "' .. currentif .. ':" | grep "media:" | head')
	output = chomp(output)
	infostr = currentif .. " (" .. detail["IPv4"]["Addresses"][1] .. " / " .. detail["IPv4"]["SubnetMasks"][1] ..")\n" .. output
	normal_alert(infostr)
	if string.match(output, "2500Base") ~= nil then
		-- it's ok.
	elseif (string.match(output, "1000base") ~= nil and currentif == "en5") or (string.match(output, "100baseTX") ~= nil and currentif == "en5") then
		hs.notify.new(reconnectEn5, {title="Slow network", informativeText="Low speed mode on en5", actionButtonTitle="Reconnect", hasActionButton=true, withdrawAfter=0}):send()
		-- logger.i("not good")
		-- warn_alert("Low speed mode for en5")
	else
		normal_alert("Unknown interface")
	end
end


-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
--   サウンドデバイス監視
-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
function CheckAirPodsBattery()
	batinfo = hs.battery.privateBluetoothBatteryInfo()
	for i, val in pairs(batinfo) do
		if string.find(val.name, "AirPods") ~= nil then
			if val.batteryPercentCase == "0" then
				info = "Battery: " .. val.batteryPercentLeft .. "%(L) / " .. val.batteryPercentRight .. "%(R)"
				valCase = "100"
			else
				info = "Battery: " .. val.batteryPercentLeft .. "%(L) / " .. val.batteryPercentRight .. "%(R), Case:" .. val.batteryPercentCase .. "%"
				valCase = val.batteryPercentCase
			end

			if tonumber(val.batteryPercentLeft) < 20 or tonumber(val.batteryPercentRight) < 20 or tonumber(valCase) < 40 then
				warn_alert(info)
			else
				normal_alert(info)
			end
		end
	end
end

function SayHello()
	hs.execute("/usr/bin/say -v Alex Hello")
end

hello_hanlde = nil
airpodsbattery_handle = nil
lastAudioDeviceChangeNotify = 0
lastSettings = nil
function audioEventCallback(arg)

	local indev = hs.audiodevice.defaultInputDevice()
	local outdev = hs.audiodevice.defaultOutputDevice()

	if arg == "dIn " then
		normal_alert("Input device was changed to [" .. indev:name() .. "]")
	elseif arg ==  "dOut" then
		ssid = hs.wifi.currentNetwork()
		if ssid == "nagakuranet2" and (string.sub(outdev:name(), 1, 7) == "MacBook" or outdev:name() == "PHL 258B6QU") then
			warn_alert("Output device was changed to [" .. outdev:name() .. "], Automatically muted")
			outdev:setMuted(true)
		else
			normal_alert("Output device was changed to [" .. outdev:name() .. "]")
		end
		local balance = outdev:balance()
		if balance ~= nil and math.abs(balance - 0.5) > 0.01 then
			warn_alert("Unbalanced output of stereo device [" .. outdev:name() .. "] " .. (balance * 1000 // 10 / 100))
			outdev:setBalance(0.5)
		end
		if outdev:name() == "kcrt's AirPods Pro" then
			outdev:setMuted(false)
			hello_handle = hs.timer.doAfter(1, SayHello)
			airpodsbattery_handle = hs.timer.doAfter(2, CheckAirPodsBattery)
		end
	elseif arg ==  "sOut" then
		-- normal_alert("System output device changed to " .. )
	elseif arg ==  "dev#" then
		local now_epoch = os.time()
		if now_epoch - lastAudioDeviceChangeNotify > 5 then
			normal_alert("Audio device configuration changed")
		end
		lastAudioDeviceChangeNotify = now_epoch
	end

	return 

end
-- local soundWatcher = hs.audiodevice.watcher.new()
hs.audiodevice.watcher.setCallback(audioEventCallback)
hs.audiodevice.watcher.start()



-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
--   P2P 緊急地震速報
-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
hConnectP2p = nil
p2peewWs = nil
function connectP2peew()
	logger.i("p2peew: connecting...")
	-- suppress p2peewWs = hs.websocket.new("wss://api.p2pquake.net/v2/ws", p2peewCallback)
end
function deg2rad(degree)
	return degree * 2 * math.pi / 360
end
function calcDistance(lat1, lon1, lat2, lon2)
	local lat1rad = deg2rad(lat1)
	local lon1rad = deg2rad(lon1)
	local lat2rad = deg2rad(lat2)
	local lon2rad = deg2rad(lon2)
	local dist = 6370 * math.acos(math.sin(lat1rad) * math.sin(lat2rad) + math.cos(lat1rad) * math.cos(lat2rad) * math.cos(lon2rad - lon1rad))
	if lat1 == -200 or lat2 == -200 then
		return -1
	elseif dist > 20000 then
		-- not on earth
		return -1
	else
		return dist
	end
end

function japanizeTsunami(tsunami)
	local tsunamiJpn = {
		None = "なし",
		Unknown = "不明",
		Checking = "確認中",
		NonEffective = "軽度",
		Watch = "注意",
		Warning = "予報"
	}
	return tsunamiJpn[tsunami]
end
function drawEarthquakeHypocenter(lat, lon, distance, scale)

	local canvas
	if distance > 80 then
		local img = hs.image.imageFromPath(os.getenv("HOME") .. "/dotfiles/map_japan.png")
		-- lon: 128 to 146, lat: 46 to 29
		local imgSize = img:size()
		img = img:setSize({w = imgSize.w / 2, h = imgSize.h / 2})
		imgSize = img:size()
		canvas = hs.canvas.new({x=0, y=0, w=imgSize.w, h=imgSize.h})
		local center = {x = (lon - 128) / (146 - 128) * imgSize.w, y = (lat - 46) / (29 - 46) * imgSize.h}

		canvas:appendElements(
			{type = "image", image = img},
			{action = "fill", center = {x = center.x, y = center.y}, fillColor={alpha=0.95, red=1.0}, radius=6, type="circle"},
			{type = "text", text = string.sub(scale, 0, 1), textColor = {white=1.0}, textSize=8, textAlignment="center", frame={x=center.x - 5, y = center.y - 6, w = 10, h = 10}}
		)
	else
		-- lon: 138.5 - 140.5, lat: 34.5-36.5
		local img = hs.image.imageFromPath(os.getenv("HOME") .. "/dotfiles/map_kanto.png")
		local imgSize = img:size()
		img = img:setSize({w = imgSize.w / 2, h = imgSize.h / 2})
		imgSize = img:size()
		canvas = hs.canvas.new({x=0, y=0, w=imgSize.w, h=imgSize.h})
		local center = {x = (lon - 138.5) / (140.5 - 138.5) * imgSize.w, y = (lat - 36.5) / (34.5 - 36.5) * imgSize.h}

		canvas:appendElements(
			{type = "image", image = img},
			{action = "fill", center = {x = center.x, y = center.y}, fillColor={alpha=0.95, red=1.0}, radius=6, type="circle"},
			{type = "text", text = string.sub(scale, 0, 1), textColor = {white=1.0}, textSize=8, textAlignment="center", frame={x=center.x - 5, y = center.y - 6, w = 10, h = 10}}
		)
	end

	return canvas:imageFromCanvas()
end

lastUserQuakeEvaluation = nil
lastOpenShindo = 0
shindoBrowser = nil
function openShindo(title)
	if os.time() - lastOpenShindo < 30 then
		-- 頻繁な通知を無視
		return false
	end
	lastOpenShindo = os.time()
	-- hs.urlevent.openURL("http://www.kmoni.bosai.go.jp")
	frame = hs.screen.primaryScreen():frame()
	w = 450
	h = 650
	x = frame["_x"] + (frame["_w"] - w) / 2
	y = frame["_y"] + (frame["_h"] - h) / 2
	shindoBrowser = hs.webview.newBrowser(hs.geometry.rect(x, y, w, h))
	shindoBrowser:windowTitle(title):url("http://www.kmoni.bosai.go.jp"):closeOnEscape(true):show():bringToFront(true):behavior(hs.drawing.windowBehaviors.canJoinAllSpaces):deleteOnClose(true)
end
function handleP2peewItem(info)
	local P2peewStyle = {}
	P2peewStyle.strokeColor = hs.drawing.color.definedCollections.hammerspoon.osx_yellow
	P2peewStyle.fillColor ={ ["red"] = 0.3,["blue"] = 0.6,["alpha"] = 0.8,["green"] = 0.6}
	P2peewStyle.strokeWidth = 10
	P2peewStyle.fadeInDuration = 0.05
	if info.code ~= nil then
		code = info.code
		if code == 551 then
			-- JMAQuake
			-- 相模大野: 35.532084,139.437684
			local scale
			local placename
			if info.earthquake.maxScale == -1 then
				scale = -1
			else
				scale = info.earthquake.maxScale / 10.0
				scale_str = string.format("%.1f", info.earthquake.maxScale / 10.0)
			end
			lat = info.earthquake.hypocenter.latitude
			lon = info.earthquake.hypocenter.longitude
			distance = calcDistance(35.532084, 139.437684, lat, lon)
			if info.earthquake.hypocenter.name == nil or info.earthquake.hypocenter.name == "" then
				placename = "？"
				if info.points ~= nil then
					if info.points[1] ~= nil then
						placename = info.points[1].addr .. "？"
					end
				end
			else
				placename = info.earthquake.hypocenter.name
			end
			distanceStr = distance == -1 and "距離不明" or string.format("%.1f [km]", distance)
			-- A and B or C   means   A ? B : C
			quake_message = "地震情報\n震源: " .. placename .. " (" .. distanceStr .. ")\n最大震度: " .. (scale == -1 and "不明" or scale_str) .. " (M" .. info.earthquake.hypocenter.magnitude .. ")\n津波: " .. japanizeTsunami(info.earthquake.domesticTsunami) .. "\n発生: " .. info.earthquake.time
			if (scale >= 3) or (scale >= 2 and distance < 100) or (scale >= 1 and distance < 30) or scale == -1 then
				-- hs.alert.show(s, hs.alert.defaultStyle, hs.screen.mainScreen(), 10)
				local img = drawEarthquakeHypocenter(lat, lon, distance, scale)
				local magnitude = info.earthquake.magnitude ~= nil and info.earthquake.magnitude or -1
				hs.sound.getByName("Sosumi"):play()
				if distance == -1 and magnitude >=3 then
					hs.alert.show(quake_message, P2peewStyle, hs.screen.mainScreen(), 10)
				else
					hs.alert.showWithImage(quake_message, img, P2peewStyle, hs.screen.mainScreen(), 10)
				end
			else
				logger.i("表示省略: " .. quake_message)
			end
		elseif code == 552 then
			-- JMATsunami
			warn_alert("津波予報発令")
			hs.sound.getByName("Submarine"):play()
		elseif code == 554 then
			-- EEWDetection
			warn_alert("緊急地震速報を検知")
			openShindo("緊急地震速報")
			hs.sound.getByName("Sosumi"):play()
		elseif code == 561 then
			-- Userquake
			local area_csv = {
				area200 = "茨城北部",
				area205 = "茨城南部",
				area210 = "栃木北部",
				area215 = "栃木南部",
				area220 = "群馬北部",
				area225 = "群馬南部",
				area230 = "埼玉北部",
				area231 = "埼玉南部",
				area232 = "埼玉秩父",
				area240 = "千葉北東部",
				area241 = "千葉北西部",
				area242 = "千葉南部",
				area250 = "東京",
				area270 = "神奈川東部",
				area275 = "神奈川西部",
				area410 = "静岡伊豆",
				area411 = "静岡東部",
				area415 = "静岡中部",
				area416 = "静岡西部",
				area520 = "岡山北部",
				area525 = "岡山南部",
				area570 = "愛媛東予",
				area575 = "愛媛中予",
				area576 = "愛媛南予"
			}
			if area_csv["area" .. info.area] ~= nil then
				-- logger.i(area_csv["area" .. info.area] .. "で地震を感知")
			end
		elseif code == 9611 then
			-- UserquakeEvaluation
			if info.confidence > 0.97 then	-- > Lv.3
				if info.started_at ~= lastUserQuakeEvaluation then
					logger.i("地震感知情報" .. dump(info))
					openShindo("地震感知情報")
					-- hs.notify.new(openShindo, {title="地震感知情報があります。", informativeText=info.started_at .. " 発生。\n情報を確認しますか？", actionButtonTitle="確認", hasActionButton=true, withdrawAfter=30}):send()
					lastUserQuakeEvaluation = info.started_at
					hs.sound.getByName("Submerge"):play()
				end
			end
		elseif code == 555 then
			-- Areapeers
		end
	elseif isArray(info) then
		-- Maybe JMAQuakes or JMATsunamis
		for value in pairs(info) do
			handleP2peewItem(value)
		end
	else
		logger.i("p2peew: unknown object")
	end
end
function p2peewCallback(operation, message)
	if operation == "open" then
		logger.i("p2peew: open")
	elseif operation == "closed" then
		logger.i("p2peew: closed")
		hConnectP2p = hs.timer.doAfter(10, connectP2peew)
	elseif operation == "fail" then
		logger.i("p2peew: fail")
		hConnectP2p = hs.timer.doAfter(10, connectP2peew)
	elseif operation == "received" then
		local timestamp = os.time()
		-- io.open("/tmp/P2PEEW_" .. timestamp .. ".json", "w"):write(message):close()
		local p2pInfo = hs.json.decode(message)
		handleP2peewItem(p2pInfo)
	else
		normal_alert("p2peew: Unknown operation " .. operation)
	end
end
hConnectP2p = hs.timer.doAfter(5, connectP2peew)

-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
--   ダウンロードフォルダ監視
-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
-- function downloadsChanged(paths, flagTables)
	-- logger.i("!!!")
	-- logger.i(dump(paths))
	-- logger.i(dump(flagTables))
-- end
-- pathWatcher = hs.pathwatcher.new(os.getenv("HOME") .. "/Downloads", downloadsChanged)
-- pathWatcher:start()

-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
--   復帰時処理
-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
function mountDrives()
	logger.i("Mount drives")
	-- mount diskimage of /Users/kcrt/diskimages/*.sparsebundle with upper case name
end
function WiredConnectionCheck()
	ipv4if, ipv6if = hs.network.primaryInterfaces()
	if ipv4if == "en8" then
		logger.i("Connected to wired network")
	else
		warn_alert("Not connected to wired network")
	end
end
function onSystemDidWake()
	logger.i("System did wake")

	if hs.screen.find("PHL 279P1") ~= nil then
		logger.i("Connected to the mother ship display")
		hs.audiodevice.findOutputByName("PHL 279P1"):setDefaultOutputDevice()
		-- check network (en8) is available after 10 sec.
		hs.timer.doAfter(10, WiredConnectionCheck)
	end
end
function onCaffeinate(eventType)
	if eventType == hs.caffeinate.watcher.systemDidWake then
		hs.timer.doAfter(10, onSystemDidWake)
	end
end
caffeinateWatcher = hs.caffeinate.watcher.new(onCaffeinate)
caffeinateWatcher:start()
hs.timer.doAfter(10, onSystemDidWake) -- 初回

-- iot every 10 minutes
-- function onIoTSended(status, body, headers)
-- 	if status ~= 200 then
-- 		logger.i("[onIoT send] " .. status)
-- 		logger.i(body)
-- 	end
-- end
-- function IoTSend()
-- 	headers = {}
-- 	headers["Content-Type"] = "application/json"
-- 
-- 	local currentmAh = io.popen("ioreg -l | grep '\"AppleRawCurrentCapacity\" = ' | sed -e 's/.* = //'", "r"):read("*a")
-- 	local maxmAh = io.popen("ioreg -l | grep '\"AppleRawMaxCapacity\" = ' | sed -e 's/.* = //'", "r"):read("*a")
-- 	local cpuload = io.popen("uptime | sed 's/.*load average.*: //' | sed 's/,/ /' | awk '{printf($1)}'", "r"):read("*a")
-- 	local url = secrets.iot_oxygen_url
-- 
-- 	hs.http.asyncPost(url .. "batteryPercentage/" .. hs.battery.percentage(), nil, headers, onIoTSended)
-- 	hs.http.asyncPost(url .. "batteryMilliAmpere/" .. chomp(currentmAh), nil, headers, onIoTSended)
-- 	hs.http.asyncPost(url .. "batteryMaxMilliAmpere/" .. chomp(maxmAh), nil, headers, onIoTSended)
-- 	hs.http.asyncPost(url .. "cpuload/" .. chomp(cpuload), nil, headers, onIoTSended)
-- 
-- 	return true
-- end
-- iotsender = hs.timer.new(60 * 10, IoTSend, true):start()
-- IoTSend()
-- TODO: hs.battery.capacity()がバッテリー使用時にどうなっているか？


lastVNCDetected = 0
function ChangeResolutionTo43()
	hs.execute("/opt/homebrew/bin/cscreen -i 2 -x 1280 -y 960 -r 30")
end
function checkVNC()
	output, status, type_, rc = hs.execute('ps aux | grep "/System/Library/CoreServices/RemoteManagement/screensharingd.bundle/Contents/MacOS/screensharingd" | grep -v "grep"')
	if rc == 0 then
		if os.time() - lastVNCDetected > 19 then
			hs.notify.new(ChangeResolutionTo43, {title="VNC Connected", informativeText="Do you want to use 4:3?", actionButtonTitle="Yes!", hasActionButton=true, withdrawAfter=60}):send()
		end
		lastVNCDetected = os.time()
	end
end
checkVNCTimer = hs.timer.new(10, checkVNC, true):start()

function onApplicationWatch(appname, eventtype, app)
	logger.i("[App] " .. eventtype .. " " .. appname)
end
-- appwatcher = hs.application.watcher.new(onApplicationWatch)
-- appwatcher:start()

function onNotification(name, object, userInfo)
	logger.i("[Notification] " .. string.format("name: %s\nobject: %s\nuserInfo: %s\n", name, object, hs.inspect(userInfo)))
end
notification_watch = hs.distributednotifications.new(onNotification)
notification_watch:start()

function onNetworkConfig(store, key)
	logger.i("[NetConf] " .. key)
end
hs.network.configuration.open():setCallback(onNetworkConfig):start()



-- mount network drives on startup
function mountDrives()
	-- mount network drives
	hs.execute("mount -t smbfs //kcrt@Drobo5N2.local/HomeVideo /Volumes/HomeVideo")

end

-- startup check
-- check if following condictions are met
--   1) connected to wifi with SSID beginning with "nanonet"
--   2) connected to wired network
--   3) connected to AC power
-- if all criteria are met, mount network drives
function checkStartup()
	logger.i("Checking startup conditions...")

	-- check wifi
	wifi = hs.wifi.currentNetwork()
	if wifi == nil then
		normal_alert("No WiFi")
		return
	end
	if string.find(wifi, "nanonet") == nil then
		normal_alert("Not connected to nanonet")
		return
	end

	-- check wired
	wired = hs.network.primaryInterfaces()
	if wired == nil then
		normal_alert("No wired network")
		return
	end
	if wired["en0"] == nil then
		normal_alert("Not connected to wired network")
		return
	end

	-- check power
	if hs.battery.powerSource() ~= "AC Power" then
		normal_alert("Not connected to AC power")
		return
	end

	-- ask to proceed
	-- hs.notify.new(mountDrives, {title="Start up", informativeText="Do you want to mount network and local drives?", actionButtonTitle="Yes!", hasActionButton=true, withdrawAfter=60}):send()
end

-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
--   Tethering Detection (iPhone hotspot)
-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

function updateTetheringBar(ssid)
	if ssid and string.find(ssid, "iPhone") then
		local orangeColor = { red = 1, green = 0.5, blue = 0, alpha = 0.8 }
		updateInformationBar("Tethering: " .. ssid, orangeColor)
	else
		removeInformationBar()
	end
end

-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
--   Information Bar (reusable visual bar)
-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
informationBar = nil

-- Create or update information bar at bottom of screen
-- text: string to display
-- color: table with {red, green, blue, alpha} values (0-1)
function createInformationBar(text, color)
	if informationBar then
		informationBar:delete()  -- Recreate to update text/color
	end

	local screen = hs.screen.primaryScreen()
	local frame = screen:fullFrame()

	-- Default to red if color not provided
	local fillColor = color or { red = 1, green = 0, blue = 0, alpha = 0.8 }

	local barHeight = 24
	informationBar = hs.canvas.new({
		x = frame.x,
		y = frame.y + frame.h - barHeight,
		w = frame.w,
		h = barHeight
	})

	informationBar[1] = {
		type = "rectangle",
		action = "fill",
		fillColor = fillColor
	}

	informationBar[2] = {
		type = "text",
		text = text,
		textColor = { white = 1 },
		textSize = 14,
		textAlignment = "center",
		frame = { x = 0, y = 2, w = frame.w, h = barHeight }
	}

	informationBar:level(hs.canvas.windowLevels.overlay)
	informationBar:behavior(hs.canvas.windowBehaviors.canJoinAllSpaces)
	informationBar:show()

	return informationBar
end

-- Update existing information bar text and/or color
function updateInformationBar(text, color)
	if informationBar then
		if text then
			informationBar[2].text = text
		end
		if color then
			informationBar[1].fillColor = color
		end
		informationBar:show()
	else
		createInformationBar(text, color)
	end
end

-- Remove information bar
function removeInformationBar()
	if informationBar then
		informationBar:delete()
		informationBar = nil
	end
end

-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
--   GPG Decryption Helper
-- -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-==-=-
function loadGPGEncryptedLua(filepath)
	-- Use full path to gpg since Hammerspoon doesn't inherit shell PATH
	local gpgPath = "/opt/homebrew/bin/gpg"
	local gpgCmd = string.format('"%s" --decrypt --batch --no-tty --quiet --yes "%s" 2>&1', gpgPath, filepath)
	local content, status, _, rc = hs.execute(gpgCmd)

	if status and content ~= nil and content ~= "" then
		local chunk, err = load(content)
		if chunk then
			chunk()
			logger.i("Successfully loaded and executed: " .. filepath)
			return true
		else
			logger.e("Failed to load Lua chunk from: " .. filepath)
			logger.e("Error: " .. tostring(err))
			return false
		end
	else
		logger.e("Failed to decrypt GPG file: " .. filepath)
		logger.e("GPG output: " .. tostring(content))
		hs.notify.new({
			title="Hammerspoon GPG Error",
			informativeText="Could not decrypt " .. filepath .. ". Please run: gpg --decrypt \"" .. filepath .. "\"",
			withdrawAfter=30
		}):send()
		return false
	end
end

-- Load private/secret functions
loadGPGEncryptedLua(os.getenv("HOME") .. "/dotfiles/secrets/private.lua.asc")
