variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, test, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be one of: dev, test, prod."
  }
}

variable "bedrock_model_id" {
  description = "Bedrock model ID (OpenAI GPT OSS 120B supports Converse tool use)"
  type        = string
  default     = "openai.gpt-oss-120b-1:0"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "api_throttle_burst_limit" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 10
}

variable "api_throttle_rate_limit" {
  description = "API Gateway throttle rate limit"
  type        = number
  default     = 5
}

variable "pushover_app_token" {
  description = "Pushover application API token"
  type        = string
  default     = ""
  sensitive   = true
}

variable "pushover_user_key" {
  description = "Pushover user key for notifications"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_oauth_client_id" {
  description = "Google OAuth 2.0 client ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_oauth_client_secret" {
  description = "Google OAuth 2.0 client secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_oauth_refresh_token" {
  description = "Google OAuth 2.0 refresh token (obtained via one-time consent flow)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_calendar_id" {
  description = "Google Calendar ID to manage interview slots"
  type        = string
  default     = "primary"
}

variable "use_custom_domain" {
  description = "Attach a custom domain to CloudFront"
  type        = bool
  default     = false
}

variable "root_domain" {
  description = "Apex domain name, e.g. mydomain.com"
  type        = string
  default     = ""
}