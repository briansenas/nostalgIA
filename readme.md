# Steps-to-connect to hugging-face
1. Create an account in hugging-face
2. Set up an access-token with the "Read access to contents of all public gated repos you can access" permission.
3. Search for the model you would like to use and accept it's "Terms of Aggreement" if so (can only use models you agree with).
4. Add the hugging-face token and model name to the code.

# Steps-to-run CUDA in the docker
Follow the instructions to install the [nvidia docker container toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html). \
Make use of the docker `compose`: `docker compose up` or, individually, `docker compose up <name>` where `<name>` can be `elasticsearch` or `streamlit`
