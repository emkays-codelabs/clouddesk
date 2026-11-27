# Non-secret settings for staging. Secrets come from TF_VAR_* environment variables, never from here.
environment   = "staging"
desired_count = 2
cpu           = 512
memory        = 1024
image_tag     = "REPLACE_WITH_GIT_SHA"
