# CloudDesk on AWS: ECR, ECS Fargate, an ALB, Secrets Manager, CloudWatch and ElastiCache Redis.
# Scaffold only: validated with `terraform validate`, never applied (CLAUDE.md 15.1).
terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {} # configured with -backend-config=backend.hcl (git-ignored)
}

provider "aws" {
  region = var.region
}

locals {
  name = "clouddesk-${var.environment}"
  tags = { project = "clouddesk", environment = var.environment }
}

data "aws_availability_zones" "available" {}

# ---- networking ----
resource "aws_vpc" "main" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_hostnames = true
  tags                 = merge(local.tags, { Name = local.name })
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false
  tags                    = local.tags
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_security_group" "lb" {
  name   = "${local.name}-lb"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "app" {
  name   = "${local.name}-app"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = 3000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.lb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---- container registry ----
resource "aws_ecr_repository" "app" {
  for_each             = toset(["backend", "frontend"])
  name                 = "${local.name}-${each.key}"
  image_tag_mutability = "IMMUTABLE" # image tags are git SHAs, never overwritten
  image_scanning_configuration {
    scan_on_push = true
  }
  tags = local.tags
}

# ---- secrets ----
resource "aws_secretsmanager_secret" "llm_api_key" {
  name = "${local.name}/llm-api-key"
  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "llm_api_key" {
  secret_id     = aws_secretsmanager_secret.llm_api_key.id
  secret_string = var.llm_api_key
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name = "${local.name}/jwt-secret"
  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = var.jwt_secret
}

# ---- monitoring ----
resource "aws_cloudwatch_log_group" "app" {
  name              = "/clouddesk/${var.environment}"
  retention_in_days = var.environment == "prod" ? 90 : 14
  tags              = local.tags
}

# ---- redis ----
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name}-redis"
  subnet_ids = aws_subnet.public[*].id
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id         = "${local.name}-redis"
  engine             = "redis"
  node_type          = "cache.t4g.micro"
  num_cache_nodes    = 1
  port               = 6379
  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.app.id]
  tags               = local.tags
}

# ---- load balancer ----
resource "aws_lb" "main" {
  name               = local.name
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.lb.id]
  tags               = local.tags
}

resource "aws_lb_target_group" "frontend" {
  name        = "${local.name}-web"
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id
  health_check {
    path = "/api/health"
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# ---- compute ----
resource "aws_ecs_cluster" "main" {
  name = local.name
  tags = local.tags
}

resource "aws_iam_role" "task_execution" {
  name = "${local.name}-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.task_execution.arn
  container_definitions = jsonencode([{
    name         = "backend"
    image        = "${aws_ecr_repository.app["backend"].repository_url}:${var.image_tag}"
    essential    = true
    portMappings = [{ containerPort = 8000 }]
    environment = [
      { name = "DEMO_MODE", value = "false" },
      { name = "REDIS_URL", value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/0" },
    ]
    secrets = [
      { name = "LLM_API_KEY", valueFrom = aws_secretsmanager_secret.llm_api_key.arn },
      { name = "JWT_SECRET", valueFrom = aws_secretsmanager_secret.jwt_secret.arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "backend"
      }
    }
  }])
}

resource "aws_ecs_service" "backend" {
  name            = "backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets         = aws_subnet.public[*].id
    security_groups = [aws_security_group.app.id]
  }
}
