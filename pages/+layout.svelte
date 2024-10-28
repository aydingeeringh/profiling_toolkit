<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	export let data;
</script>

<EvidenceDefaultLayout 
    {data} 
    fullWidth={true}
    logo="static/images/logo.png"
>
	<slot slot="content" />
</EvidenceDefaultLayout>
