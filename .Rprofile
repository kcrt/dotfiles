# options(device="quartz")

setHook(packageEvent("grDevices", "onLoad"),
	function(...){
		if(.Platform$OS.type == "windows"){
			grDevices::windowsFonts(
				sans ="MS Gothic",
				serif="MS Mincho",
				mono ="FixedFont"
			);
		}else if(capabilities("aqua")){
			grDevices::quartzFonts(
				sans= grDevices::quartzFont(
						c("Hiragino Kaku Gothic Pro W3",
						"Hiragino Kaku Gothic Pro W6",
						"Hiragino Kaku Gothic Pro W3",
						"Hiragino Kaku Gothic Pro W6")
						),
				serif=grDevices::quartzFont(
						c("Hiragino Mincho Pro W3",
						"Hiragino Mincho Pro W6",
						"Hiragino Mincho Pro W3",
						"Hiragino Mincho Pro W6")
						)
				);
		}else if(capabilities("X11")){
			grDevices::X11.options(fonts=c("-kochi-gothic-%s-%s-*-*-%d-*-*-*-*-*-*-*",
				"-adobe-symbol-medium-r-*-*-%d-*-*-*-*-*-*-*"))
		}
		grDevices::pdf.options(family="Japan1")
		grDevices::ps.options(family="Japan1")
	}
)

attach(NULL, name = "JapanEnv")
assign("familyset_hook",
	function() {
		winfontdevs=c("windows","win.metafile", "png","bmp","jpeg","tiff")
		macfontdevs=c("quartz","quartz_off_screen")
		devname=strsplit(names(dev.cur()),":")[[1L]][1]
		if ((.Platform$OS.type == "windows") && (devname %in% winfontdevs)){
			par(family="sans")
		}else if (capabilities("aqua") && devname %in% macfontdevs){
			par(family="sans")
		}
	},
	pos="JapanEnv");

setHook("plot.new", get("familyset_hook", pos="JapanEnv"))
setHook("persp", get("familyset_hook", pos="JapanEnv"))
