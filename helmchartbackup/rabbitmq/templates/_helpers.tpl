{{- define "rabbitmq.name" -}}
rabbitmq-wrcbot
{{- end }}

{{- define "rabbitmq.fullname" -}}
{{ .Release.Name }}-rabbitmq
{{- end }}