{{- define "redis.name" -}}
redis-wrcbot
{{- end }}

{{- define "redis.fullname" -}}
{{ .Release.Name }}-redis
{{- end }}