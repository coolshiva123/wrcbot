{{- define "wrcbot.name" -}}
wrcbot
{{- end }}

{{- define "wrcbot.fullname" -}}
{{ .Release.Name }}-wrcbot
{{- end }}