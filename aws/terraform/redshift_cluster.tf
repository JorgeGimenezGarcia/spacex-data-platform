provider "aws" {
  region = "us-west-2"
}

resource "aws_redshift_cluster" "spacex_dw" {
  cluster_identifier   = "spacex-redshift"
  database_name        = "spacexdb"
  master_username      = "adminuser"           # In prod, store in Secrets Manager
  master_password      = "SuperSecret123"     # Use Secrets Manager in real deployments
  node_type            = "ra3.xlplus"         # RA3 for separated storage and compute
  cluster_type         = "multi-node"
  number_of_nodes      = 2
  publicly_accessible  = false
  encrypted            = true
  # network configuration (VPC, subnets, SG) should be added in a full deployment
}

# In practice, add:
# - aws_redshift_subnet_group, aws_security_group
# - aws_iam_role for S3 access
# - aws_secretsmanager_secret for credentials