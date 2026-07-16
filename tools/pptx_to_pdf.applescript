-- pptx_to_pdf.applescript
-- Convert a PPTX to PDF using Microsoft PowerPoint's native renderer - the same
-- engine as File > Export > "Best for printing", but automated (no manual clicks).
-- Preserves the deck's slide dimensions (Claude Design sets 960x540pt = 16:9).
--
-- Usage: osascript tools/pptx_to_pdf.applescript <abs_in.pptx> <abs_out.pdf>
--
-- One-time setup: the first run triggers a macOS prompt
--   "Terminal (or your shell) wants to control Microsoft PowerPoint" - click OK.
--   (System Settings > Privacy & Security > Automation remembers it after that.)

on run argv
	if (count of argv) < 2 then error "usage: osascript pptx_to_pdf.applescript <in.pptx> <out.pdf>"
	set inPath to item 1 of argv
	set outPath to item 2 of argv
	set outHFS to (POSIX file outPath) as text
	tell application "Microsoft PowerPoint"
		activate
		open (POSIX file inPath)
		set pres to active presentation
		save pres in outHFS as save as PDF
		close pres saving no
	end tell
	return "wrote " & outPath
end run
