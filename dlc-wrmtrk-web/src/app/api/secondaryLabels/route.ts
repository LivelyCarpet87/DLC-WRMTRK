export async function GET(request: Request) {
  // For example, fetch data from your DB here
  const secondaryLabels = [ "Team_1", "Team_2", "Team_3"  ];
  return new Response(JSON.stringify(secondaryLabels), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}