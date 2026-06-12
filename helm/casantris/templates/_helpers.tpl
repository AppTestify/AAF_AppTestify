{{- define "casantris.secretName" -}}
{{- if .Values.secrets.existingSecretName -}}
{{ .Values.secrets.existingSecretName }}
{{- else -}}
{{ .Chart.Name }}-secrets
{{- end -}}
{{- end -}}
