JsOsaDAS1.001.00bplist00�Vscript_�const Music = Application('Music');

selectedTracks = Music.selection();
selectedTracks.forEach((track) => {
    track.trackNumber = track.trackNumber() + 1;
});
                            �jscr  ��ޭ