# Non-secret settings for prod. Secrets come from TF_VAR_* environment variables, never from here.
environment   = "prod"
desired_count = 2
cpu           = 1024
memory        = 2048
image_tag     = "REPLACE_WITH_GIT_SHA"
