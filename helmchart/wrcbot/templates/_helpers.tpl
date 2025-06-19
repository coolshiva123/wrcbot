{{- define "wrcbot.name" -}}
wrcbot-wrcbot
{{- end }}

{{- define "wrcbot.fullname" -}}
{{ .Release.Name }}-wrcbot
{{- end }}