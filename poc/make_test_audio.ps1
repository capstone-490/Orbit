# Generates test.wav from sample_input.txt using the built-in Windows text-to-speech voice.
# Run from the folder that contains sample_input.txt.
Add-Type -AssemblyName System.Speech
$text = Get-Content -Path "sample_input.txt" -Raw
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile("test.wav")
$synth.Speak($text)
$synth.Dispose()
Write-Host "Created test.wav"
